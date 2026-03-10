import json
import os
import re
from groq import Groq
from textwrap import dedent
from src.get_vars import get_data

GROQ_MODEL = get_data("model")
MAX_CONTEXT = get_data("MAX_CONTEXT_MESSAGES")

"""
Singleton client pattern avoids recreating Groq instance on each call.
API key loaded from environment (handled by Groq SDK).
"""
client = None


def get_client():
    global client
    if client is None:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return client


"""
Emoji regex covers multiple Unicode ranges: emoticons, symbols, skin tones,
variation selectors. Used to count emoji frequency per message (raw stat).
"""
EMOJI_PATTERN = re.compile(
    "[\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f6ff"
    "\U0001f1e0-\U0001f1ff"
    "\U00002702-\U000027b0"
    "\U000024c2-\U0001f251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2b55"
    "\u200d\u23cf\u23e9\u231a\ufe0f\u3030]+",
    flags=re.UNICODE,
)


def ollama_chat(system_prompt, user_prompt, temperature=0.2):
    """
    Function name is 'ollama_chat' for backward compatibility with code expecting
    that interface, but implementation uses Groq API. Groq models are faster than
    local Ollama and support streaming. Temperature capped at 1.0 (Groq constraint).
    Max tokens fixed at 1024 to bound response length and API cost.
    """
    response = get_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=min(temperature, 1.0),
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def extract_json(raw: str) -> dict:
    """
    Extract JSON from model response using multiple strategies:
    1. Strip markdown fences and try direct parse
    2. Regex search for innermost {...} object (handles partial responses)
    3. Return sensible defaults (avoid downstream crashes)

    Strategy 2 is critical: models sometimes wrap JSON in extra text or
    newlines. Non-greedy [^{}]+ only matches single-level objects, avoiding
    nested JSON issues that could break parsing.
    """
    cleaned = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[^{}]+\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {
        "chaos_score": 50,
        "toxicity_score": 10,
        "eloquence_score": 50,
        "expressiveness_score": 50,
        "social_score": 50,
        "consistency_score": 50,
    }


def clamp(value, lo=0.0, hi=100.0):
    """Ensure value stays within bounds. Guards against LLM scores outside 0-100."""
    return max(lo, min(hi, value))


def compute_raw_stats(texts):
    """
    Compute linguistic markers: message length, vocabulary diversity, capitalization,
    and emoji frequency. These serve as objective signals before LLM scoring.

    Lexical diversity includes a dampening factor for small datasets:
    (unique_words / total_words) * min(1.0, len(texts) / 50)
    This prevents artificial inflation when analyzing less than 50 messages.

    Returns tuple: (avg_message_length, lexical_diversity, uppercase_ratio, emoji_per_message)
    """
    if not texts:
        return 0, 0, 0, 0

    total_words = 0
    unique_words = set()
    total_letters = 0
    uppercase_letters = 0
    emoji_count = 0

    for message in texts:
        words = message.lower().split()
        total_words += len(words)
        unique_words.update(words)

        for c in message:
            if c.isalpha():
                total_letters += 1
                if c.isupper():
                    uppercase_letters += 1

        emoji_count += len(EMOJI_PATTERN.findall(message))

    avg_length = total_words / len(texts)
    lexical_diversity = (
        (len(unique_words) / total_words) * min(1.0, len(texts) / 50)
        if total_words
        else 0
    )
    uppercase_ratio = uppercase_letters / total_letters if total_letters else 0
    emoji_per_message = emoji_count / len(texts)

    return avg_length, lexical_diversity, uppercase_ratio, emoji_per_message


def scores_to_metrics(scores, messages):
    """
    Convert LLM scoring dict + raw stats into unified metrics object.
    Clamps scores to 0-100 range and adds computed linguistic markers.
    message_count included for downstream filtering (e.g., ignore archetypes for less than 20 messages).
    """
    avg_len, lex_div, upper_ratio, emoji_per_msg = compute_raw_stats(messages)
    return {
        "chaos_score": clamp(float(scores.get("chaos_score", 50))),
        "toxicity_score": clamp(float(scores.get("toxicity_score", 10))),
        "eloquence_score": clamp(float(scores.get("eloquence_score", 50))),
        "expressiveness_score": clamp(float(scores.get("expressiveness_score", 50))),
        "social_score": clamp(float(scores.get("social_score", 50))),
        "consistency_score": clamp(float(scores.get("consistency_score", 50))),
        "raw_avg_message_length": avg_len,
        "raw_lexical_diversity": lex_div,
        "raw_uppercase_ratio": upper_ratio,
        "raw_emoji_per_message": emoji_per_msg,
        "message_count": len(messages),
    }


def compute_metrics(messages, context=None):
    """
    Score messages on six dimensions. Context can be a formatted conversation log
    (richer, includes reply relationships) or simple message list.

    Prompt design:
    - Opens with role definition to anchor behavior
    - Explicitly disambiguates banter/sarcasm (not toxic) to reduce false positives
    - Defines scoring dimensions with concrete examples
    - Requests ONLY JSON to simplify extraction

    Temperature 0.2 ensures consistent, deterministic scoring.
    Uses MAX_CONTEXT to respect Groq token limits.
    """
    if context and context.get("log"):
        context_section = dedent(
            f"""CONVERSATION LOG:
                Legend: >>> = target user's messages, [re:N] = reply to message N
                {context['log']}"""
        ).strip()
    else:
        messages_block = "\n".join(f"  - {m}" for m in messages[:MAX_CONTEXT])
        context_section = f"MESSAGES (showing up to {MAX_CONTEXT}):\n{messages_block}"

    prompt = dedent(
        f"""You are a behavioral analysis AI. Analyze the following Discord messages and rate the target user on 6 dimensions.

            {context_section}

            Use context and timestamps to understand intent. Banter, sarcasm, gaming trash talk = not toxic.

            Rate 0-100:
            - chaos_score: Unpredictability, erratic lengths, caps, topic jumps
            - toxicity_score: Genuine hostility (not jokes/banter)
            - eloquence_score: Vocabulary richness, articulation
            - expressiveness_score: Emojis, exclamations, emotional intensity
            - social_score: Mentions, questions, back-and-forth engagement
            - consistency_score: Uniform style and message length

            Reply ONLY with this JSON, no explanation:
            {{"chaos_score": 0, "toxicity_score": 0, "eloquence_score": 0, "expressiveness_score": 0, "social_score": 0, "consistency_score": 0}}"""
    ).strip()

    raw = ollama_chat(
        system_prompt="You are a behavioral analysis AI. Output only raw JSON, no markdown, no explanation.",
        user_prompt=prompt,
        temperature=0.2,
    )

    scores = extract_json(raw)
    return scores_to_metrics(scores, messages)


def analyze_and_roast(messages, context):
    """
    Two-phase analysis: compute scores AND generate a roast.
    Pre-compute raw stats to feed into prompt for grounded observations.

    Prompt tricks:
    - Inline raw_stats with parenthetical labels (e.g., "(caps lock warrior)") to cue persona
    - Explicit rules about referencing conversation (look up original message, don't say "[re:N]")
    - Format requirement (<scores> and <roast> tags) to split response cleanly
    - Temperature 0.9 for creative, varied roasts

    Fallback roast if extraction fails: acknowledges failure gracefully.
    """
    log = context.get("log", "No conversation data available.")
    username = context.get("target", "this user")

    avg_len, _, upper_ratio, emoji_per_msg = compute_raw_stats(messages)

    prompt = dedent(
        f"""You are Dr. Unhinged, a behavioral analyst embedded in a Discord bot.
            Analyze the conversation log below and do TWO things:

            1. Score the target user (>>>) on 6 dimensions (0-100)
            2. Write a roast based on their actual behavior in this conversation

            CONVERSATION LOG:
            Legend: >>> = {username}'s messages, [re:N] = reply to message N, numbers are message IDs
            {log}

            RAW STATS (pre-computed):
            - Avg message length: {avg_len:.1f} words {"(essay writer)" if avg_len > 25 else "(man of few words)" if avg_len < 4 else ""}
            - Uppercase ratio: {upper_ratio:.0%} {"(caps lock warrior)" if upper_ratio > 0.2 else ""}
            - Emoji per message: {emoji_per_msg:.1f} {"(emoji factory)" if emoji_per_msg > 3 else ""}

            SCORING DIMENSIONS:
            - chaos_score: Unpredictability, erratic lengths, caps, topic jumps
            - toxicity_score: Genuine hostility only (banter/jokes = not toxic)
            - eloquence_score: Vocabulary richness, articulation
            - expressiveness_score: Emojis, exclamations, emotional intensity
            - social_score: Mentions, questions, back-and-forth engagement
            - consistency_score: Uniform style and message length

            ROAST RULES:
            - Write like a chaotic Gen Z therapist. Lowercase hits harder, ALL CAPS for drama, emojis for emphasis
            - When referencing a reply, look up the original message in the log and describe it naturally. Never say "msg [N]" or "[re:N]" in the roast — say what actually happened. e.g. instead of "bro replied to msg [1]" say "bro replied to a simple 'hi' with..."            - Reference specific message numbers when the burn is good ("bro saw message [42] and responded with...")
            - Different timestamps = different days = different topics, don't mix them up
            - Affectionate destruction only — funny, not cruel. 6-10 punchy lines, no intro fluff

            Respond in this EXACT format and nothing else:
            <scores>
            {{"chaos_score": 0, "toxicity_score": 0, "eloquence_score": 0, "expressiveness_score": 0, "social_score": 0, "consistency_score": 0}}
            </scores>
            <roast>
            your roast here
            </roast>"""
    ).strip()

    raw = ollama_chat(
        system_prompt=(
            "You are Dr. Unhinged, a Discord behavioral analyst. "
            "You always respond in the exact format requested with <scores> and <roast> tags."
        ),
        user_prompt=prompt,
        temperature=0.9,
    )

    """
    Extract tagged sections from response. If format is broken, fallback to
    treating entire response as one section. Non-greedy .*? avoids over-matching
    across multiple tags if they somehow appear twice.
    """
    scores_match = re.search(r"<scores>\s*(.*?)\s*</scores>", raw, re.DOTALL)
    roast_match = re.search(r"<roast>\s*(.*?)\s*</roast>", raw, re.DOTALL)

    scores_raw = scores_match.group(1) if scores_match else ""
    roast_text = roast_match.group(1).strip() if roast_match else raw.strip()

    scores = extract_json(scores_raw) if scores_raw else extract_json(raw)
    metrics = scores_to_metrics(scores, messages)

    """
    Guard against empty or truncated roasts (model hallucination or timeout).
    Fallback message acknowledges the failure and lets metrics speak for themselves.
    """
    if not roast_text or len(roast_text) < 20:
        roast_text = f"_(Dr. Unhinged lost the plot trying to analyze {username}. The numbers alone tell the story.)_"

    return {"metrics": metrics, "roast": roast_text}

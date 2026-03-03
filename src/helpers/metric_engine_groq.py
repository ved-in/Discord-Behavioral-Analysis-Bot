import json
import os
import re
from groq import Groq
from textwrap import dedent
from src.get_vars import get_data

GROQ_MODEL = get_data("model")
MAX_CONTEXT = get_data("MAX_CONTEXT_MESSAGES")
client = None

def get_client():
    global client
    if client is None:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return client   

EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d\u23cf\u23e9\u231a\ufe0f\u3030]+",
    flags=re.UNICODE
)


def ollama_chat(system_prompt, user_prompt, temperature=0.2):
    """Named ollama_chat for drop-in compatibility but uses Groq under the hood."""
    response = get_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=min(temperature, 1.0),
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def extract_json(raw: str) -> dict:
    """Try multiple strategies to extract a JSON object from a model response."""
    cleaned = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[^{}]+\}', cleaned, re.DOTALL)
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
    return max(lo, min(hi, value))


def compute_raw_stats(texts):
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
        if total_words else 0
    )
    uppercase_ratio = uppercase_letters / total_letters if total_letters else 0
    emoji_per_message = emoji_count / len(texts)

    return avg_length, lexical_diversity, uppercase_ratio, emoji_per_message


def scores_to_metrics(scores, messages):
    avg_len, lex_div, upper_ratio, emoji_per_msg = compute_raw_stats(messages)
    return {
        "chaos_score":          clamp(float(scores.get("chaos_score", 50))),
        "toxicity_score":       clamp(float(scores.get("toxicity_score", 10))),
        "eloquence_score":      clamp(float(scores.get("eloquence_score", 50))),
        "expressiveness_score": clamp(float(scores.get("expressiveness_score", 50))),
        "social_score":         clamp(float(scores.get("social_score", 50))),
        "consistency_score":    clamp(float(scores.get("consistency_score", 50))),
        "raw_avg_message_length": avg_len,
        "raw_lexical_diversity":  lex_div,
        "raw_uppercase_ratio":    upper_ratio,
        "raw_emoji_per_message":  emoji_per_msg,
        "message_count": len(messages),
    }


def compute_metrics(messages, context=None):
    if context and context.get("log"):
        context_section = dedent(
            f"""CONVERSATION LOG:
                Legend: >>> = target user's messages, [re:N] = reply to message N
                {context['log']}"""
        ).strip()
    else:
        messages_block = "\n".join(f"  - {m}" for m in messages[:MAX_CONTEXT])
        context_section = f"MESSAGES (showing up to 60):\n{messages_block}"

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

    scores_match = re.search(r'<scores>\s*(.*?)\s*</scores>', raw, re.DOTALL)
    roast_match = re.search(r'<roast>\s*(.*?)\s*</roast>', raw, re.DOTALL)

    scores_raw = scores_match.group(1) if scores_match else ""
    roast_text = roast_match.group(1).strip() if roast_match else raw.strip()

    scores = extract_json(scores_raw) if scores_raw else extract_json(raw)
    metrics = scores_to_metrics(scores, messages)

    if not roast_text or len(roast_text) < 20:
        roast_text = f"_(Dr. Unhinged lost the plot trying to analyze {username}. The numbers alone tell the story.)_"

    return {"metrics": metrics, "roast": roast_text}
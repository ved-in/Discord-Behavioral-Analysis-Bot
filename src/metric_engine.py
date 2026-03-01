import json
import os
import re
from groq import Groq
from textwrap import dedent

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

def make_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")
    return Groq(api_key=api_key)

groq_client = None

def get_groq_client():
    global groq_client
    if groq_client is None:
        groq_client = make_client()
    return groq_client


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
    uppercase_ratio = (
        uppercase_letters / total_letters if total_letters else 0
    )
    emoji_per_message = emoji_count / len(texts)

    return avg_length, lexical_diversity, uppercase_ratio, emoji_per_message


def format_context_block(context_snippets, sample_size=40):
    sample = context_snippets[:sample_size]
    return "\n\n".join(f"[exchange {i+1}]\n{snippet}" for i, snippet in enumerate(sample))


def compute_metrics(messages, context_snippets=None):
    context_snippets = context_snippets or []

    if context_snippets:
        context_block = format_context_block(context_snippets)
        context_section = dedent(
            f"""
                CONVERSATION CONTEXT (each exchange shows what the user was responding to;
                their message is marked with >>>):
                {context_block}"""
            ).strip()
    else:
        messages_block = "\n".join(f"  - {m}" for m in messages[:80])
        context_section = dedent(
            f"""MESSAGES ({len(messages)} total, showing up to 80):
                {messages_block}"""
            ).strip()

    prompt = dedent(
        f"""You are a behavioral analysis AI. Analyze the following Discord messages from a single user and rate them on 6 behavioral dimensions.

            {context_section}

            Important: Use the conversation context to understand *intent*. A user saying "I WILL DESTROY YOU" in response to a game challenge is very different from genuine aggression. Sarcasm, irony, in-jokes, and hype should all be read in context before scoring.

            Rate each dimension from 0 to 100 based on the actual messages and their context.

            DIMENSION DEFINITIONS:
            - chaos_score: How unpredictable, erratic, or unhinged their communication style is. High = wild message length swings, lots of caps, exclamations, rapid topic jumps.
            - toxicity_score: How hostile or genuinely aggressive their language is *in context*. Don't penalize obvious jokes, banter, or hype. High = real insults, sustained aggression, targeted negativity.
            - eloquence_score: How articulate and vocabulary-rich they are. High = long thoughtful messages, varied vocabulary, good structure.
            - expressiveness_score: How emotionally expressive they are. High = lots of emojis, exclamations, intensity markers, emotional language.
            - social_score: How conversational and social they are. High = lots of mentions, questions, short back-and-forth style.
            - consistency_score: How uniform and predictable their style is. High = similar message lengths, stable tone throughout.

            Respond ONLY with a valid JSON object, no explanation, no markdown, no extra text:
            {{"chaos_score": 0, "toxicity_score": 0, "eloquence_score": 0, "expressiveness_score": 0, "social_score": 0, "consistency_score": 0}}"""    
        ).strip()

    client = get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a behavioral analysis AI. You only respond with raw JSON, no markdown, no explanation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=200,
    )

    raw = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
    try:
        scores = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Groq returned invalid JSON: {e}\nRaw response: {raw[:200]}") from e
    avg_len, lex_div, upper_ratio, emoji_per_msg = compute_raw_stats(messages)

    return {
        "chaos_score": clamp(float(scores.get("chaos_score", 0))),
        "toxicity_score": clamp(float(scores.get("toxicity_score", 0))),
        "eloquence_score": clamp(float(scores.get("eloquence_score", 0))),
        "expressiveness_score": clamp(float(scores.get("expressiveness_score", 0))),
        "social_score": clamp(float(scores.get("social_score", 0))),
        "consistency_score": clamp(float(scores.get("consistency_score", 0))),
        "raw_avg_message_length": avg_len,
        "raw_lexical_diversity": lex_div,
        "raw_uppercase_ratio": upper_ratio,
        "raw_emoji_per_message": emoji_per_msg,
        "message_count": len(messages),
    }


def generate_roast(username, context_snippets, metrics, archetype):
    context_block = format_context_block(context_snippets)

    prompt = dedent(
        f"""You are Dr. Unhinged — a brutally funny AI behavioral analyst embedded in a Discord bot.
            Your job is to roast a Discord user based on their actual messages AND the conversations they were part of.

            You write like a chaotic Gen Z therapist who has given up on professionalism but not on accuracy.
            Use Discord-style language: lowercase when it hits harder, emojis for emphasis, occasional ALL CAPS for drama.

            CRITICAL — be contextually aware:
            - Read what they were RESPONDING TO before judging their message
            - Call out patterns across multiple exchanges, not just isolated messages
            - If they always say unhinged stuff in calm conversations — roast that
            - If they're the chaos starter vs the chaos responder — roast that differently
            - Reference SPECIFIC exchanges when the burn is good enough ("bro responded to 'how's your day' with...")
            - The more specific and contextual the burn, the funnier it is

            Do NOT be mean-spirited or genuinely hurtful. The vibe is "affectionate destruction", like a best friend roasting you.
            Keep it to 6-10 punchy lines. No intro fluff. Start roasting immediately.

            USER: {username}
            ARCHETYPE: {archetype['emoji']} {archetype['name']}

            THEIR CONVERSATIONS (>>> marks their message, preceding lines are context):
            {context_block}

            BEHAVIORAL METRICS (0-100, AI-analyzed):
            - Chaos Score: {metrics["chaos_score"]:.0f} {"(UNHINGED)" if metrics["chaos_score"] > 60 else "(suspiciously calm)"}
            - Eloquence: {metrics["eloquence_score"]:.0f} {"(actually reads books??)" if metrics["eloquence_score"] > 60 else "(not a literary threat)"}
            - Expressiveness: {metrics["expressiveness_score"]:.0f}
            - Social Score: {metrics["social_score"]:.0f} {"(mentions everyone, always)" if metrics["social_score"] > 60 else ""}
            - Consistency: {metrics["consistency_score"]:.0f} {"(robot behavior detected)" if metrics["consistency_score"] > 85 else ""}
            - Toxicity: {metrics["toxicity_score"]:.0f} {"(yikes)" if metrics["toxicity_score"] > 50 else ""}
            - Avg message length: {metrics["raw_avg_message_length"]:.1f} words {"(essay writer)" if metrics["raw_avg_message_length"] > 25 else "(man of few words)" if metrics["raw_avg_message_length"] < 4 else ""}
            - Uppercase ratio: {metrics["raw_uppercase_ratio"]:.0%} {"(the caps lock is load-bearing)" if metrics["raw_uppercase_ratio"] > 0.2 else ""}
            - Emoji per message: {metrics["raw_emoji_per_message"]:.1f} {"(communicates in hieroglyphics)" if metrics["raw_emoji_per_message"] > 3 else ""}

            Now roast them. Full chaos. No mercy. But keep it funny, not cruel.
            Start immediately, no preamble."""
        ).strip()

    client = get_groq_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Dr. Unhinged, a chaotic but accurate Discord behavioral analyst. You roast people based on real conversational data. You are funny, specific, contextually aware, and ruthless but never genuinely cruel."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.2,
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return (
            f"_(Dr. Unhinged tried to roast {username} but something went wrong: `{e}`)_\n\n"
            f"Fallback verdict: **{archetype['emoji']} {archetype['name']}** — "
            f"the data speaks for itself and honestly it's not looking great."
        )
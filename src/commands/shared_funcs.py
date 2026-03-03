import asyncio, os

from src.get_vars import get_data

provider = get_data("provider")
if provider == "ollama":
    from src.helpers.metric_engine import analyze_and_roast, compute_metrics
elif provider == "groq":
    from src.helpers.metric_engine_groq import analyze_and_roast, compute_metrics
else:
    print("Provider in config.json MUST BE either groq or ollama.")
    os._exit(1)

from src.helpers.archetype_classifier import classify
from src.get_vars import get_data
MIN_MESSAGES = get_data("MIN_MESSAGES")
DEFAULT_ANALYZE_LIMIT = get_data("ANALYZE_LIMIT")
HISTORY_MULTIPLIER = get_data("HISTORY_MULTIPLIER")


async def collect_messages(channel, target, limit=DEFAULT_ANALYZE_LIMIT):
    raw = []
    id_to_index = {}

    async for msg in channel.history(limit=limit * HISTORY_MULTIPLIER):
        if msg.content.strip() and not msg.author.bot:
            raw.append(msg)

    raw.reverse()
    raw = raw[-limit:]

    for i, msg in enumerate(raw, start=1):
        id_to_index[msg.id] = i

    messages = []
    for msg in raw:
        if msg.author.id == target.id:
            messages.append(msg.content)

    lines = []
    for i, msg in enumerate(raw, start=1):
        timestamp = msg.created_at.strftime("%m-%d %H:%M")
        prefix = ">>>" if msg.author.id == target.id else "   "

        reply_part = ""
        if msg.reference and msg.reference.message_id in id_to_index:
            reply_part = f" [re:{id_to_index[msg.reference.message_id]}]"

        content = msg.content[:120] + "…" if len(msg.content) > 120 else msg.content
        lines.append(f"{prefix}[{i}]{reply_part} {timestamp} {msg.author.display_name}: {content}")

    return messages, {"log": "\n".join(lines), "target": target.display_name}


async def collect_all_messages(channel, limit=DEFAULT_ANALYZE_LIMIT):
    user_messages = {}
    async for msg in channel.history(limit=limit):
        if not msg.content.strip() or msg.author.bot:
            continue
        uid = msg.author.id
        if uid not in user_messages:
            user_messages[uid] = {"member": msg.author, "messages": []}
        user_messages[uid]["messages"].append(msg.content)
    return user_messages


async def analyze_member(channel, member, limit=DEFAULT_ANALYZE_LIMIT):
    messages, context = await collect_messages(channel, member, limit)
    if len(messages) < MIN_MESSAGES:
        return None
    metrics = await asyncio.to_thread(compute_metrics, messages, context)
    return {
        "messages": messages,
        "context": context,
        "metrics": metrics,
        "archetype": classify(metrics),
    }


async def analyze_member_with_roast(channel, member, limit=DEFAULT_ANALYZE_LIMIT):
    messages, context = await collect_messages(channel, member, limit)
    if len(messages) < MIN_MESSAGES:
        return None
    result = await asyncio.to_thread(analyze_and_roast, messages, context)
    return {
        "messages": messages,
        "context": context,
        "metrics": result["metrics"],
        "roast": result["roast"],
        "archetype": classify(result["metrics"]),
    }

import asyncio
import discord
import os
from discord import app_commands
from dotenv import load_dotenv

from src.metric_engine import analyze_and_roast, compute_metrics
from src.archetype_classifier import classify
from src.radar_chart import generate_chart, generate_comparison_chart

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

MIN_MESSAGES = 10


async def collect_messages(channel, target, limit=150):
    raw = []
    id_to_index = {}

    async for msg in channel.history(limit=limit * 5):
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

        if msg.author.id == target.id:
            prefix = ">>>"
        else:
            prefix = "   "

        reply_part = ""
        if msg.reference and msg.reference.message_id in id_to_index:
            replied_to_index = id_to_index[msg.reference.message_id]
            reply_part = f" [re:{replied_to_index}]"

        content = msg.content
        if len(content) > 120:
            content = content[:120] + "…"

        line = f"{prefix}[{i}]{reply_part} {timestamp} {msg.author.display_name}: {content}"
        lines.append(line)

    context = {
        "log": "\n".join(lines),
        "target": target.display_name,
    }

    return messages, context


async def collect_all_messages(channel, limit=300):
    user_messages = {}
    async for msg in channel.history(limit=limit):
        if not msg.content.strip() or msg.author.bot:
            continue
        uid = msg.author.id
        if uid not in user_messages:
            user_messages[uid] = {"member": msg.author, "messages": []}
        user_messages[uid]["messages"].append(msg.content)
    return user_messages


async def analyze_member(channel, member, limit=150):
    messages, context = await collect_messages(channel, member, limit)

    if len(messages) < MIN_MESSAGES:
        return None

    metrics = await asyncio.to_thread(compute_metrics, messages, context)
    archetype = classify(metrics)

    return {
        "messages": messages,
        "context": context,
        "metrics": metrics,
        "archetype": archetype
    }

async def analyze_member_with_roast(channel, member, limit=150):
    messages, context = await collect_messages(channel, member, limit)

    if len(messages) < MIN_MESSAGES:
        return None
    result = await asyncio.to_thread(analyze_and_roast, messages, context)
    archetype = classify(result["metrics"])

    return {
        "messages": messages,
        "context": context,
        "metrics": result["metrics"],
        "roast": result["roast"],
        "archetype": archetype,
    }

def score_line(label, value, width=12):
    filled = round((value / 100) * width)
    bar = "█" * filled + "░" * (width - filled)

    while len(label) < 15:
        label += " "

    result = "`" + label + "` " + bar + " **" + str(round(value)) + "**"
    return result


def build_profile_embed(target, metrics, archetype, message_count):
    embed = discord.Embed(
        title=f"{archetype['emoji']} {target.display_name} — {archetype['name']}",
        description=(
            f"{archetype['description']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Analyzed **{message_count}** messages"
        ),
        color=archetype["color"]
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="📊 Behavioral Scores", value="\n".join([
        score_line("Chaos",          metrics["chaos_score"]),
        score_line("Eloquence",      metrics["eloquence_score"]),
        score_line("Expressiveness", metrics["expressiveness_score"]),
        score_line("Social",         metrics["social_score"]),
        score_line("Consistency",    metrics["consistency_score"]),
        score_line("Toxicity",       metrics["toxicity_score"]),
    ]), inline=False)
    embed.add_field(name="🔬 Stats", value=(
        f"**Msg length** `{metrics['raw_avg_message_length']:.1f} words`\n"
        f"**Lex diversity** `{metrics['raw_lexical_diversity']:.2f}`\n"
        f"**Uppercase** `{metrics['raw_uppercase_ratio']:.1%}`\n"
        f"**Emojis/msg** `{metrics['raw_emoji_per_message']:.2f}`"
    ), inline=True)
    embed.add_field(name="🏷️ Traits", value="\n".join(f"▸ {t}" for t in archetype["traits"]), inline=True)
    embed.set_footer(text="Behavioral Analysis Engine • powered by Ollama (llama3.2)")
    return embed


def build_comparison_embed(user1, metrics1, archetype1, user2, metrics2, archetype2):
    embed = discord.Embed(
        title=f"⚔️ {user1.display_name}  vs  {user2.display_name}",
        description="Head-to-head behavioral profile comparison",
        color=0x9932CC
    )

    def row(label, v1, v2):
        arrow = "▲" if v1 > v2 else "▼" if v1 < v2 else "="
        return f"`{label:<15}` `{v1:>7.0f}` {arrow} `{v2:<7.0f}`"

    n1, n2 = user1.display_name[:8], user2.display_name[:8]
    rows = "\n".join([
        f"`{'':15}` `{n1:>8}` `{n2:>8}`",
        row("Chaos",          metrics1["chaos_score"],          metrics2["chaos_score"]),
        row("Eloquence",      metrics1["eloquence_score"],      metrics2["eloquence_score"]),
        row("Expressiveness", metrics1["expressiveness_score"], metrics2["expressiveness_score"]),
        row("Social",         metrics1["social_score"],         metrics2["social_score"]),
        row("Consistency",    metrics1["consistency_score"],    metrics2["consistency_score"]),
        row("Toxicity",       metrics1["toxicity_score"],       metrics2["toxicity_score"]),
    ])
    embed.add_field(name="📊 Score Comparison", value=rows, inline=False)
    for user, archetype in [(user1, archetype1), (user2, archetype2)]:
        embed.add_field(
            name=f"{archetype['emoji']} {user.display_name}",
            value=f"**{archetype['name']}**\n" + "\n".join(f"▸ {t}" for t in archetype["traits"]),
            inline=True
        )
    embed.set_footer(text="Behavioral Analysis Engine • powered by Ollama (llama3.2)")
    return embed


@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")


@tree.command(name="analyze", description="Run a behavioral analysis on a user.")
async def analyze(interaction: discord.Interaction, user: discord.Member = None, limit: int = 150):
    await interaction.response.defer(thinking=True)

    target = user or interaction.user
    limit = max(20, min(300, limit))

    result = await analyze_member(interaction.channel, target, limit)

    if not result:
        await interaction.followup.send(
            f"Not enough messages for {target.display_name} (need {MIN_MESSAGES})."
        )
        return

    metrics = result["metrics"]
    archetype = result["archetype"]
    messages = result["messages"]

    chart_path = await asyncio.to_thread(generate_chart, metrics, target.display_name)

    embed = build_profile_embed(target, metrics, archetype, len(messages))
    file = discord.File(chart_path, filename="profile.png")
    embed.set_image(url="attachment://profile.png")
    try:
        await interaction.followup.send(embed=embed, file=file)
    finally:
        os.remove(chart_path)


@tree.command(name="roast", description="Get roasted based on your behavior.")
async def roast(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer(thinking=True)

    target = user or interaction.user

    result = await analyze_member_with_roast(interaction.channel, target)

    if not result:
        await interaction.followup.send(
            f"Not enough messages to roast properly (need {MIN_MESSAGES})."
        )
        return

    archetype = result["archetype"]
    roast_text = result["roast"]

    embed = discord.Embed(
        title=f"{target.display_name} has been analyzed",
        description=roast_text,
        color=archetype["color"]
    )
    await interaction.followup.send(embed=embed)


@tree.command(name="compare", description="Compare two users.")
async def compare(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
    await interaction.response.defer(thinking=True)

    r1 = await analyze_member(interaction.channel, user1)
    r2 = await analyze_member(interaction.channel, user2)

    if not r1 or not r2:
        await interaction.followup.send(
            f"Both users need at least {MIN_MESSAGES} messages."
        )
        return

    chart_path = generate_comparison_chart(
        r1["metrics"], user1.display_name,
        r2["metrics"], user2.display_name
    )

    try:
        embed = build_comparison_embed(
            user1, r1["metrics"], r1["archetype"],
            user2, r2["metrics"], r2["archetype"]
        )
        file = discord.File(chart_path, filename="comparison.png")
        embed.set_image(url="attachment://comparison.png")
        await interaction.followup.send(embed=embed, file=file)
    finally:
        os.remove(chart_path)


@tree.command(name="leaderboard", description="Show the most chaotic/toxic/interesting users in this channel.")
@app_commands.describe(metric="Which metric to rank by", limit="How many users to scan (default 50)")
@app_commands.choices(metric=[
    app_commands.Choice(name="Chaos Score",     value="chaos_score"),
    app_commands.Choice(name="Toxicity Score",  value="toxicity_score"),
    app_commands.Choice(name="Eloquence Score", value="eloquence_score"),
    app_commands.Choice(name="Social Score",    value="social_score"),
])
async def leaderboard(interaction: discord.Interaction, metric: str = "chaos_score", limit: int = 50):
    await interaction.response.defer(thinking=True)

    user_messages = await collect_all_messages(interaction.channel, limit=limit * 5)
    scores = []
    for data in user_messages.values():
        if len(data["messages"]) < MIN_MESSAGES:
            continue
        metrics = await asyncio.to_thread(compute_metrics, data["messages"], [])
        scores.append((data["member"], metrics.get(metric, 0)))

    scores.sort(key=lambda x: x[1], reverse=True)
    top = scores[:10]

    if not top:
        await interaction.followup.send("Not enough active users in this channel to build a leaderboard.")
        return

    label = metric.replace("_score", "").replace("_", " ").title()
    medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7

    embed = discord.Embed(
        title=f"Leaderboard — {label}",
        description=f"Top users ranked by **{label}** in #{interaction.channel.name}",
        color=discord.Color.gold()
    )
    for i, (member, score) in enumerate(top):
        embed.add_field(name=f"{medals[i]} {member.display_name}", value=f"{score:.1f}", inline=True)

    embed.set_footer(text=f"Analyzed {len(scores)} active users")
    await interaction.followup.send(embed=embed)


token = os.getenv("DISCORD_TOKEN")
bot.run(token)
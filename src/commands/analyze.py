import discord, asyncio, os

from src.helpers.bot_instance import tree
from src.commands.shared_funcs import analyze_member, MIN_MESSAGES
from src.helpers.radar_chart import generate_chart

from src.get_vars import get_data

DEFAULT_ANALYZE_LIMIT = get_data("ANALYZE_LIMIT")


@tree.command(name="analyze", description="Run a behavioral analysis on a user.")
async def analyze(interaction: discord.Interaction, user: discord.Member = None, limit: int = DEFAULT_ANALYZE_LIMIT):
    await interaction.response.defer(thinking=True)

    target = user or interaction.user
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


def build_profile_embed(target, metrics, archetype, message_count):
    embed = discord.Embed(
        title=f"{archetype['emoji']} {target.display_name} — {archetype['name']}",
        description=(
            f"{archetype['description']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Analyzed **{message_count}** messages"
        ),
        color=archetype["color"],
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="📊 Behavioral Scores", value="\n".join([
        score_line("Chaos", metrics["chaos_score"]),
        score_line("Eloquence", metrics["eloquence_score"]),
        score_line("Expressiveness", metrics["expressiveness_score"]),
        score_line("Social", metrics["social_score"]),
        score_line("Consistency", metrics["consistency_score"]),
        score_line("Toxicity", metrics["toxicity_score"]),
    ]), inline=False)
    embed.add_field(name="🔬 Stats", value=(
        f"**Msg length** `{metrics['raw_avg_message_length']:.1f} words`\n"
        f"**Lex diversity** `{metrics['raw_lexical_diversity']:.2f}`\n"
        f"**Uppercase** `{metrics['raw_uppercase_ratio']:.1%}`\n"
        f"**Emojis/msg** `{metrics['raw_emoji_per_message']:.2f}`"
    ), inline=True)
    embed.add_field(
        name="🏷️ Traits",
        value="\n".join(f"▸ {t}" for t in archetype["traits"]),
        inline=True,
    )
    embed.set_footer(text="Behavioral Analysis Engine • powered by Groq (llama3.3)")
    return embed

def score_line(label, value, width=12):
    filled = round((value / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"`{label:<15}` {bar} **{round(value)}**"

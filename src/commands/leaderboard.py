import discord, asyncio
from discord import app_commands

from src.helpers.bot_instance import tree
from src.commands.shared_funcs import collect_all_messages, compute_metrics, MIN_MESSAGES


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

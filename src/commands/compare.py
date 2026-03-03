import discord, os
from src.helpers.bot_instance import tree

from src.commands.shared_funcs import analyze_member, MIN_MESSAGES
from src.helpers.radar_chart import generate_comparison_chart


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


def build_comparison_embed(user1, metrics1, archetype1, user2, metrics2, archetype2):
    embed = discord.Embed(
        title=f"⚔️ {user1.display_name}  vs  {user2.display_name}",
        description="Head-to-head behavioral profile comparison",
        color=0x9932CC,
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
            inline=True,
        )
    embed.set_footer(text="Behavioral Analysis Engine • powered by Groq (llama3.3)")
    return embed

import discord

from src.helpers.bot_instance import tree
from src.commands.shared_funcs import analyze_member_with_roast, MIN_MESSAGES


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

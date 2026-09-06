from __future__ import annotations

import discord

from .config import COLOUR_DANGER, COLOUR_PRIMARY, COLOUR_SUCCESS, COLOUR_WARNING


def embed(
    title: str,
    description: str = "",
    colour: int = COLOUR_PRIMARY,
) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=colour)


def success(title: str, description: str) -> discord.Embed:
    return embed(title, description, COLOUR_SUCCESS)


def warning(title: str, description: str) -> discord.Embed:
    return embed(title, description, COLOUR_WARNING)


def danger(title: str, description: str) -> discord.Embed:
    return embed(title, description, COLOUR_DANGER)


def member_name(member: discord.abc.User) -> str:
    return getattr(member, "display_name", member.name)


async def send_error(interaction: discord.Interaction, message: str) -> None:
    content = f"ليس لديك صلاحية لاستخدام هذا الأمر.\n{message}"
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)
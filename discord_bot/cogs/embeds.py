from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..database import Database
from ..utils import embed


MAX_EMBED_MESSAGE_LENGTH = 4096


class Embeds(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot

    @app_commands.command(name="embed", description="إرسال رسالة بشكل Embed")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(message="النص الذي سيظهر داخل الـ Embed")
    async def send_embed(
        self,
        interaction: discord.Interaction,
        message: app_commands.Range[str, 1, MAX_EMBED_MESSAGE_LENGTH],
    ) -> None:
        await interaction.channel.send(
            embed=embed("رسالة", message),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await interaction.response.send_message(
            "تم إرسال الرسالة على شكل Embed.",
            ephemeral=True,
        )

    @commands.command(name="embed")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_embed(
        self, ctx: commands.Context[commands.Bot], *, message: str
    ) -> None:
        if len(message) > MAX_EMBED_MESSAGE_LENGTH:
            await ctx.send(
                f"النص طويل جدًا. الحد الأقصى هو {MAX_EMBED_MESSAGE_LENGTH} حرفًا.",
                delete_after=8,
            )
            return
        await ctx.send(
            embed=embed("رسالة", message),
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Embeds(bot, database))
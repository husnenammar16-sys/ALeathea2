from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..database import Database
from ..utils import embed


MAX_EMBED_MESSAGE_LENGTH = 4096
MAX_EMBED_TITLE_LENGTH = 256


class Embeds(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot

    @app_commands.command(name="embed", description="إرسال رسالة بشكل Embed")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        title="العنوان الذي سيظهر في أعلى الـ Embed",
        message="نص الرسالة الذي سيظهر داخل الـ Embed",
    )
    async def send_embed(
        self,
        interaction: discord.Interaction,
        title: app_commands.Range[str, 1, MAX_EMBED_TITLE_LENGTH],
        message: app_commands.Range[str, 1, MAX_EMBED_MESSAGE_LENGTH],
    ) -> None:
        await interaction.channel.send(
            embed=embed(title, message),
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
        self, ctx: commands.Context[commands.Bot], *, content: str
    ) -> None:
        if "|" not in content:
            await ctx.send(
                "الاستخدام الصحيح: `!embed العنوان | نص الرسالة`.",
                delete_after=8,
            )
            return

        title, message = (part.strip() for part in content.split("|", 1))
        if not title or not message:
            await ctx.send(
                "اكتب العنوان ونص الرسالة بهذا الشكل: `!embed العنوان | نص الرسالة`.",
                delete_after=8,
            )
            return
        if len(title) > MAX_EMBED_TITLE_LENGTH:
            await ctx.send(
                f"العنوان طويل جدًا. الحد الأقصى هو {MAX_EMBED_TITLE_LENGTH} حرفًا.",
                delete_after=8,
            )
            return
        if len(message) > MAX_EMBED_MESSAGE_LENGTH:
            await ctx.send(
                f"النص طويل جدًا. الحد الأقصى هو {MAX_EMBED_MESSAGE_LENGTH} حرفًا.",
                delete_after=8,
            )
            return
        await ctx.send(
            embed=embed(title, message),
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Embeds(bot, database))
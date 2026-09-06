from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from ..config import COLOUR_DANGER
from ..database import Database
from ..utils import embed
from .logs import send_log


class AutoMod(commands.Cog):
    automod = app_commands.Group(name="automod", description="إدارة الحماية التلقائية")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database
        self.recent: dict[tuple[int, int], tuple[str, float]] = {}

    @automod.command(name="setup", description="تفعيل الحماية من السبام والروابط")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_automod(self, interaction: discord.Interaction) -> None:
        self.database.set_setting(interaction.guild_id, "automod_enabled", 1)
        await interaction.response.send_message(
            embed=embed("تم تفعيل الحماية", "سيتم التعامل مع تكرار الرسائل، المنشن المزعج، وبعض الروابط الخطرة."),
            ephemeral=True,
        )

    @automod.command(name="disable", description="تعطيل الحماية التلقائية")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable_automod(self, interaction: discord.Interaction) -> None:
        self.database.set_setting(interaction.guild_id, "automod_enabled", 0)
        await interaction.response.send_message("تم تعطيل الحماية التلقائية.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return
        settings = self.database.get_settings(message.guild.id)
        if not settings["automod_enabled"]:
            return
        content = message.content.lower().strip()
        key = (message.guild.id, message.author.id)
        previous = self.recent.get(key)
        now = time.monotonic()
        self.recent[key] = (content, now)
        reason = None
        if previous and previous[0] == content and now - previous[1] < 10:
            reason = "تكرار الرسالة"
        elif len(message.mentions) >= 6:
            reason = "منشن مزعج"
        elif "discord.gg/" in content and not message.author.guild_permissions.manage_messages:
            reason = "رابط دعوة غير مسموح"
        if not reason:
            return
        try:
            await message.delete()
            warning = await message.channel.send(
                embed=embed("تم حذف رسالة", f"{message.author.mention} تم حذف الرسالة بسبب: **{reason}**.", COLOUR_DANGER)
            )
            await warning.delete(delay=8)
            await send_log(self.bot, self.database, message.guild, "حماية تلقائية", f"{message.author} — {reason}", COLOUR_DANGER)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(AutoMod(bot, database))
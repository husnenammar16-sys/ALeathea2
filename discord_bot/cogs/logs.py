from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..config import COLOUR_DANGER, COLOUR_PRIMARY, COLOUR_SUCCESS, COLOUR_WARNING
from ..database import Database
from ..utils import embed


async def send_log(
    bot: commands.Bot,
    database: Database,
    guild: discord.Guild,
    title: str,
    description: str,
    colour: int = COLOUR_PRIMARY,
) -> None:
    settings = database.get_settings(guild.id)
    channel_id = settings["logs_channel_id"]
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if isinstance(channel, discord.TextChannel):
        await channel.send(embed=embed(title, description, colour))


class Logs(commands.Cog):
    logs = app_commands.Group(name="logs", description="إعداد سجل الأحداث")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database

    @logs.command(name="setup", description="تحديد قناة اللوقز")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="قناة تسجيل الأحداث")
    async def setup_logs(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        self.database.set_setting(interaction.guild_id, "logs_channel_id", channel.id)
        await interaction.response.send_message(
            embed=embed("تم إعداد اللوقز", f"سيتم تسجيل الأحداث في {channel}."),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await send_log(
            self.bot,
            self.database,
            member.guild,
            "دخول عضو جديد",
            f"انضم {member.mention} إلى السيرفر.",
            COLOUR_SUCCESS,
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await send_log(
            self.bot,
            self.database,
            member.guild,
            "خروج عضو",
            f"غادر **{member}** السيرفر.",
            COLOUR_WARNING,
        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild and not message.author.bot:
            await send_log(
                self.bot,
                self.database,
                message.guild,
                "حذف رسالة",
                f"العضو: {message.author.mention}\nالقناة: {message.channel.mention}\n"
                f"المحتوى: {message.content[:1000] or 'رسالة بدون نص'}",
                COLOUR_DANGER,
            )

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        if (
            before.guild
            and not before.author.bot
            and before.content != after.content
        ):
            await send_log(
                self.bot,
                self.database,
                before.guild,
                "تعديل رسالة",
                f"العضو: {before.author.mention}\nالقناة: {before.channel.mention}\n"
                f"قبل: {before.content[:500] or 'فارغة'}\nبعد: {after.content[:500] or 'فارغة'}",
                COLOUR_WARNING,
            )


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Logs(bot, database))
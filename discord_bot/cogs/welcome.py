from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..config import COLOUR_SUCCESS
from ..database import Database
from ..utils import embed


class Welcome(commands.Cog):
    welcome = app_commands.Group(name="welcome", description="إعداد رسائل الترحيب")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database

    @welcome.command(name="setup", description="تحديد قناة الترحيب")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="القناة التي ستستقبل الأعضاء الجدد")
    async def setup_welcome(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        self.database.set_setting(interaction.guild_id, "welcome_channel_id", channel.id)
        await interaction.response.send_message(
            embed=embed("تم إعداد الترحيب", f"ستصل رسائل الترحيب إلى {channel}."),
            ephemeral=True,
        )

    @welcome.command(name="disable", description="تعطيل الترحيب")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable_welcome(self, interaction: discord.Interaction) -> None:
        self.database.set_setting(interaction.guild_id, "welcome_channel_id", None)
        await interaction.response.send_message(
            embed=embed("تم تعطيل الترحيب", "لن يرسل البوت رسائل ترحيب حتى تعيد تفعيله."),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        settings = self.database.get_settings(member.guild.id)
        channel_id = settings["welcome_channel_id"]
        role_id = settings["autorole_id"]

        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="رتبة تلقائية عند الدخول")
                except discord.HTTPException:
                    pass

        if not channel_id:
            return
        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        card = embed(
            f"مرحبًا بك في {member.guild.name}",
            f"أهلًا بك {member.mention}، نتمنى لك وقتًا ممتعًا معنا.",
            COLOUR_SUCCESS,
        )
        card.set_thumbnail(url=member.display_avatar.url)
        card.add_field(name="أعضاء السيرفر", value=str(member.guild.member_count), inline=True)
        card.add_field(name="العضو الجديد", value=member_name(member), inline=True)
        await channel.send(embed=card)


def member_name(member: discord.Member) -> str:
    return member.display_name


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Welcome(bot, database))
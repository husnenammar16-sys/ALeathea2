from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from ..config import BOT_NAME
from ..database import Database
from ..utils import embed, member_name


class General(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database

    @app_commands.command(name="help", description="عرض جميع أوامر البوت")
    async def help(self, interaction: discord.Interaction) -> None:
        message = (
            "**أوامر عامة لكل الأعضاء**\n"
            "`/help` `/ping` `/server` `/user` `/avatar`\n"
            "`/balance` `/daily` `/work` `/pay` `/rich` `/profile`\n"
            "`/rank` `/leaderboard` `/coinflip` `/roll` `/eightball` `/choose`\n"
            "`/ticket` لفتح تذكرة و`/suggest send` لإرسال اقتراح.\n\n"
            "**أوامر الإدارة فقط**\n"
            "`/ticket setup` `/suggest setup` `/logs setup`\n"
            "`/welcome setup` `/welcome disable`\n"
            "`/autorole setup` `/autorole disable` `/reactionrole setup`\n"
            "`/automod setup` `/automod disable`\n"
            "`/giveaway start` `/giveaway end`\n"
            "`/custom add` `/custom remove` `/custom list`\n"
            "`/call` لإرسال نداء خاص إلى عضو\n"
            "`/voice join` `/voice leave` للتحكم بالروم الصوتي والبقاء الدائم\n"
            "`/ban` `/kick` `/timeout` `/untimeout` `/warn` `/warnings`\n"
            "`/clearwarnings` `/clear` `/lock` `/unlock`\n\n"
            "الأوامر الإدارية محمية بصلاحيات Discord المناسبة."
        )
        await interaction.response.send_message(
            embed=embed(f"{BOT_NAME} • مركز المساعدة", message), ephemeral=True
        )

    @app_commands.command(name="ping", description="عرض سرعة استجابة البوت")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            embed=embed("سرعة الاستجابة", f"زمن الاستجابة: **{latency}ms**")
        )

    @app_commands.command(name="server", description="عرض معلومات السيرفر")
    async def server(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        created = discord.utils.format_dt(guild.created_at, style="D")
        card = embed(f"معلومات {guild.name}", "نظرة سريعة على مجتمعك")
        if guild.icon:
            card.set_thumbnail(url=guild.icon.url)
        card.add_field(name="المالك", value=f"<@{guild.owner_id}>", inline=True)
        card.add_field(name="الأعضاء", value=str(guild.member_count), inline=True)
        card.add_field(name="القنوات", value=str(len(guild.channels)), inline=True)
        card.add_field(name="تاريخ الإنشاء", value=created, inline=False)
        await interaction.response.send_message(embed=card)

    @app_commands.command(name="user", description="عرض معلومات عضو")
    @app_commands.describe(member="العضو المطلوب")
    async def user(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        target = member or interaction.user
        card = embed(f"معلومات {member_name(target)}", f"المعرّف: `{target.id}`")
        card.set_thumbnail(url=target.display_avatar.url)
        card.add_field(name="الاسم", value=target.mention, inline=True)
        card.add_field(
            name="انضم في", value=discord.utils.format_dt(target.joined_at, style="D"), inline=True
        )
        card.add_field(name="الرتب", value=str(max(len(target.roles) - 1, 0)), inline=True)
        await interaction.response.send_message(embed=card)

    @app_commands.command(name="avatar", description="عرض صورة عضو")
    @app_commands.describe(member="العضو المطلوب")
    async def avatar(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        target = member or interaction.user
        card = embed(f"صورة {member_name(target)}")
        card.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=card)


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(General(bot, database))
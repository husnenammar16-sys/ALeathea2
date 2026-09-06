from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ..database import Database
from ..utils import embed, member_name
from .levels import profile_embed


def remaining_time(value: str | None, cooldown: timedelta) -> str | None:
    if not value:
        return None
    elapsed = datetime.now(UTC) - datetime.fromisoformat(value)
    remaining = cooldown - elapsed
    if remaining.total_seconds() <= 0:
        return None
    minutes = max(1, int(remaining.total_seconds() // 60))
    return f"{minutes} دقيقة"


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.database = database

    @app_commands.command(name="balance", description="عرض رصيدك أو رصيد عضو")
    @app_commands.describe(member="عضو اختياري")
    async def balance(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        row = self.database.get_economy(interaction.guild_id, target.id)
        await interaction.response.send_message(
            embed=embed("الرصيد", f"رصيد **{member_name(target)}** هو **{row['balance']:,}** عملة.")
        )

    @app_commands.command(name="daily", description="استلام مكافأة يومية")
    async def daily(self, interaction: discord.Interaction) -> None:
        row = self.database.get_economy(interaction.guild_id, interaction.user.id)
        wait = remaining_time(row["last_daily"], timedelta(hours=24))
        if wait:
            await interaction.response.send_message(f"استلمت مكافأتك مسبقًا. حاول بعد **{wait}**.", ephemeral=True)
            return
        amount = random.randint(150, 300)
        balance = self.database.change_balance(interaction.guild_id, interaction.user.id, amount)
        self.database.set_economy_date(
            interaction.guild_id, interaction.user.id, "last_daily", datetime.now(UTC).isoformat()
        )
        await interaction.response.send_message(
            embed=embed("المكافأة اليومية", f"حصلت على **{amount}** عملة.\nرصيدك الآن: **{balance:,}**.")
        )

    @app_commands.command(name="work", description="اعمل لتحصل على عملات")
    async def work(self, interaction: discord.Interaction) -> None:
        row = self.database.get_economy(interaction.guild_id, interaction.user.id)
        wait = remaining_time(row["last_work"], timedelta(minutes=30))
        if wait:
            await interaction.response.send_message(f"تحتاج إلى الراحة قليلًا. حاول بعد **{wait}**.", ephemeral=True)
            return
        amount = random.randint(40, 120)
        balance = self.database.change_balance(interaction.guild_id, interaction.user.id, amount)
        self.database.set_economy_date(
            interaction.guild_id, interaction.user.id, "last_work", datetime.now(UTC).isoformat()
        )
        jobs = ["صممت شعارًا", "ساعدت عضوًا جديدًا", "أنجزت مهمة", "نظمت فعالية"]
        await interaction.response.send_message(
            embed=embed("تم إنجاز العمل", f"لقد **{random.choice(jobs)}** وحصلت على **{amount}** عملة.\nرصيدك: **{balance:,}**.")
        )

    @app_commands.command(name="pay", description="تحويل عملات إلى عضو")
    @app_commands.describe(member="المستلم", amount="مبلغ التحويل")
    async def pay(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 1_000_000]) -> None:
        if member.bot or member.id == interaction.user.id:
            await interaction.response.send_message("اختر عضوًا حقيقيًا غير نفسك.", ephemeral=True)
            return
        sender = self.database.get_economy(interaction.guild_id, interaction.user.id)
        if sender["balance"] < amount:
            await interaction.response.send_message("رصيدك لا يكفي لهذا التحويل.", ephemeral=True)
            return
        self.database.change_balance(interaction.guild_id, interaction.user.id, -amount)
        self.database.change_balance(interaction.guild_id, member.id, amount)
        await interaction.response.send_message(f"تم تحويل **{amount:,}** عملة إلى {member.mention}.")

    @app_commands.command(name="rich", description="عرض أغنى أعضاء السيرفر")
    async def rich(self, interaction: discord.Interaction) -> None:
        rows = self.database.economy_leaderboard(interaction.guild_id)
        lines = [
            f"**{index}.** <@{row['user_id']}> — {row['balance']:,} عملة"
            for index, row in enumerate(rows, start=1)
        ]
        await interaction.response.send_message(
            embed=embed("أغنى أعضاء السيرفر", "\n".join(lines) or "لا توجد أرصدة بعد.")
        )

    @app_commands.command(name="profile", description="عرض ملفك في المجتمع")
    @app_commands.describe(member="عضو اختياري")
    async def profile(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        money = self.database.get_economy(interaction.guild_id, target.id)
        card = profile_embed(self.database, interaction.guild_id, target)
        card.add_field(name="الرصيد", value=f"{money['balance']:,}", inline=True)
        await interaction.response.send_message(embed=card)


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Economy(bot, database))
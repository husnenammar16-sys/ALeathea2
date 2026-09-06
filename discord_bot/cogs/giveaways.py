from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ..config import COLOUR_SUCCESS, COLOUR_WARNING
from ..database import Database
from ..utils import embed


class GiveawayView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(
        label="مشاركة",
        style=discord.ButtonStyle.success,
        emoji="🎉",
        custom_id="alythia:giveaway:enter",
    )
    async def enter(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        giveaway = next(
            (
                row
                for row in self.database.active_giveaways()
                if row["message_id"] == interaction.message.id
            ),
            None,
        )
        if not giveaway:
            await interaction.response.send_message("هذه السحبة انتهت.", ephemeral=True)
            return
        added = self.database.add_giveaway_entry(giveaway["id"], interaction.user.id)
        await interaction.response.send_message(
            "تم تسجيل مشاركتك في السحبة!" if added else "أنت مشارك بالفعل في هذه السحبة.",
            ephemeral=True,
        )


class Giveaways(commands.Cog):
    giveaway = app_commands.Group(name="giveaway", description="إدارة السحوبات")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database
        self.finish_loop.start()

    def cog_unload(self) -> None:
        self.finish_loop.cancel()

    @giveaway.command(name="start", description="بدء سحبة جديدة")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(minutes="مدة السحبة بالدقائق", prize="الجائزة")
    async def start(
        self,
        interaction: discord.Interaction,
        minutes: app_commands.Range[int, 1, 10080],
        prize: str,
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("هذا الأمر يعمل في قناة نصية فقط.", ephemeral=True)
            return
        ends_at = datetime.now(UTC) + timedelta(minutes=minutes)
        giveaway_id = self.database.create_giveaway(
            interaction.guild_id, interaction.channel.id, prize, ends_at.isoformat()
        )
        card = embed(
            "سحبة جديدة 🎉",
            f"**الجائزة:** {prize}\n**تنتهي:** {discord.utils.format_dt(ends_at, style='R')}\n"
            f"اضغط الزر للمشاركة.\n\nرقم السحبة: `{giveaway_id}`",
            COLOUR_SUCCESS,
        )
        message = await interaction.channel.send(embed=card, view=GiveawayView(self.database))
        self.database.set_giveaway_message(giveaway_id, message.id)
        await interaction.response.send_message("تم بدء السحبة.", ephemeral=True)

    @giveaway.command(name="end", description="إنهاء سحبة واختيار فائز")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(giveaway_id="رقم السحبة")
    async def end(self, interaction: discord.Interaction, giveaway_id: int) -> None:
        result = await self.finish_giveaway(giveaway_id)
        await interaction.response.send_message(result, ephemeral=True)

    async def finish_giveaway(self, giveaway_id: int) -> str:
        giveaway = self.database.get_giveaway(giveaway_id)
        if not giveaway or giveaway["ended"]:
            return "هذه السحبة غير موجودة أو منتهية."
        self.database.end_giveaway(giveaway_id)
        participants = self.database.giveaway_entries(giveaway_id)
        winner_id = random.choice(participants) if participants else None
        guild = self.bot.get_guild(giveaway["guild_id"])
        if guild:
            channel = guild.get_channel(giveaway["channel_id"])
            if isinstance(channel, discord.TextChannel) and giveaway["message_id"]:
                try:
                    message = await channel.fetch_message(giveaway["message_id"])
                    card = embed(
                        "انتهت السحبة",
                        f"**الجائزة:** {giveaway['prize']}\n"
                        + (
                            f"الفائز: <@{winner_id}> 🎉"
                            if winner_id
                            else "لم يشارك أي عضو في السحبة."
                        ),
                        COLOUR_WARNING,
                    )
                    await message.edit(embed=card, view=None)
                    if winner_id:
                        await channel.send(f"مبروك <@{winner_id}>! فزت بـ **{giveaway['prize']}**.")
                except discord.HTTPException:
                    pass
        return f"تم إنهاء السحبة. {'الفائز: <@' + str(winner_id) + '>' if winner_id else 'لا يوجد مشاركون.'}"

    @tasks.loop(seconds=30)
    async def finish_loop(self) -> None:
        now = datetime.now(UTC)
        for giveaway in self.database.active_giveaways():
            if datetime.fromisoformat(giveaway["ends_at"]) <= now:
                await self.finish_giveaway(giveaway["id"])

    @finish_loop.before_loop
    async def before_finish_loop(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Giveaways(bot, database))
    bot.add_view(GiveawayView(database))
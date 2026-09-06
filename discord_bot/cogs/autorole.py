from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..database import Database
from ..utils import embed


class AutoRole(commands.Cog):
    autorole = app_commands.Group(name="autorole", description="إعداد الرتبة التلقائية")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.database = database

    @autorole.command(name="setup", description="تحديد رتبة للأعضاء الجدد")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(role="الرتبة التي سيحصل عليها العضو الجديد")
    async def setup_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if role.managed:
            await interaction.response.send_message("لا يمكن استخدام رتبة مرتبطة بتكامل خارجي.", ephemeral=True)
            return
        self.database.set_setting(interaction.guild_id, "autorole_id", role.id)
        await interaction.response.send_message(
            embed=embed("تم إعداد الرتبة التلقائية", f"سيحصل الأعضاء الجدد على {role}."),
            ephemeral=True,
        )

    @autorole.command(name="disable", description="تعطيل الرتبة التلقائية")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def disable_role(self, interaction: discord.Interaction) -> None:
        self.database.set_setting(interaction.guild_id, "autorole_id", None)
        await interaction.response.send_message(
            embed=embed("تم تعطيل الرتبة التلقائية", "لن تتم إضافة رتبة تلقائيًا."), ephemeral=True
        )


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(AutoRole(bot, database))
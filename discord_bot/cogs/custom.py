from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..database import Database
from ..utils import embed


class CustomCommands(commands.Cog):
    custom = app_commands.Group(name="custom", description="إدارة الأوامر المخصصة")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.database = database

    @custom.command(name="add", description="إضافة أمر مخصص يبدأ بعلامة !")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(name="اسم الأمر بدون !", response="الرد الذي سيرسله البوت")
    async def add(self, interaction: discord.Interaction, name: str, response: str) -> None:
        clean_name = name.strip().lower().replace(" ", "-")
        if not clean_name.isalnum() and "-" not in clean_name:
            await interaction.response.send_message("استخدم حروفًا وأرقامًا فقط لاسم الأمر.", ephemeral=True)
            return
        self.database.set_custom_command(interaction.guild_id, clean_name, response)
        await interaction.response.send_message(
            embed=embed("تمت إضافة الأمر", f"استخدم الأمر داخل الدردشة هكذا: `!{clean_name}`"),
            ephemeral=True,
        )

    @custom.command(name="remove", description="حذف أمر مخصص")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(name="اسم الأمر بدون !")
    async def remove(self, interaction: discord.Interaction, name: str) -> None:
        removed = self.database.delete_custom_command(interaction.guild_id, name)
        await interaction.response.send_message(
            "تم حذف الأمر." if removed else "لم أجد هذا الأمر.", ephemeral=True
        )

    @custom.command(name="list", description="عرض الأوامر المخصصة")
    async def list_commands(self, interaction: discord.Interaction) -> None:
        rows = self.database.list_custom_commands(interaction.guild_id)
        names = "\n".join(f"`!{row['name']}`" for row in rows) or "لا توجد أوامر مخصصة."
        await interaction.response.send_message(embed=embed("الأوامر المخصصة", names), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot or not message.content.startswith("!"):
            return
        name = message.content[1:].split(maxsplit=1)[0].lower()
        row = self.database.custom_command(message.guild.id, name)
        if not row:
            return
        response = row["response"].replace("{user}", message.author.mention)
        await message.channel.send(response)


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(CustomCommands(bot, database))
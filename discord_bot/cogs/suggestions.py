from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..config import COLOUR_DANGER, COLOUR_SUCCESS
from ..database import Database
from ..utils import embed


class SuggestionView(discord.ui.View):
    def __init__(self, database: Database, suggestion_id: int) -> None:
        super().__init__(timeout=None)
        self.database = database
        self.suggestion_id = suggestion_id

    @discord.ui.button(label="قبول", style=discord.ButtonStyle.success, emoji="👍")
    async def approve(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("ليس لديك صلاحية لاتخاذ قرار في الاقتراحات.", ephemeral=True)
            return
        self.database.update_suggestion_status(self.suggestion_id, "accepted")
        await self._update(interaction, "مقبول", COLOUR_SUCCESS)

    @discord.ui.button(label="رفض", style=discord.ButtonStyle.danger, emoji="👎")
    async def reject(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("ليس لديك صلاحية لاتخاذ قرار في الاقتراحات.", ephemeral=True)
            return
        self.database.update_suggestion_status(self.suggestion_id, "rejected")
        await self._update(interaction, "مرفوض", COLOUR_DANGER)

    async def _update(self, interaction: discord.Interaction, status: str, colour: int) -> None:
        message = interaction.message
        if message and message.embeds:
            card = message.embeds[0]
            card.colour = colour
            card.add_field(name="النتيجة", value=status, inline=False)
            await interaction.response.edit_message(embed=card, view=None)
        else:
            await interaction.response.send_message(f"تم تسجيل الاقتراح كـ {status}.", ephemeral=True)


class Suggestions(commands.Cog):
    suggest = app_commands.Group(name="suggest", description="إدارة الاقتراحات")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.database = database

    @suggest.command(name="setup", description="تحديد قناة الاقتراحات")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="القناة التي ستظهر فيها الاقتراحات")
    async def setup_suggestions(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        self.database.set_setting(interaction.guild_id, "suggestions_channel_id", channel.id)
        await interaction.response.send_message(
            embed=embed("تم إعداد الاقتراحات", f"ستظهر الاقتراحات في {channel}."), ephemeral=True
        )

    @suggest.command(name="send", description="إرسال اقتراح جديد")
    @app_commands.describe(content="اكتب اقتراحك للمجتمع")
    async def send_suggestion(self, interaction: discord.Interaction, content: str) -> None:
        settings = self.database.get_settings(interaction.guild_id)
        channel = interaction.guild.get_channel(settings["suggestions_channel_id"]) if settings["suggestions_channel_id"] else None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "لم يتم إعداد قناة الاقتراحات بعد. اطلب من الإدارة استخدام `/suggest setup`.",
                ephemeral=True,
            )
            return
        suggestion_id = self.database.add_suggestion(interaction.guild_id, interaction.user.id, content)
        card = embed(
            f"اقتراح جديد #{suggestion_id}",
            content,
        )
        card.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        card.add_field(name="الحالة", value="قيد المراجعة", inline=False)
        message = await channel.send(embed=card, view=SuggestionView(self.database, suggestion_id))
        self.database.set_suggestion_message(suggestion_id, message.id)
        await interaction.response.send_message(f"تم إرسال اقتراحك إلى {channel}.", ephemeral=True)


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Suggestions(bot, database))
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..config import COLOUR_PRIMARY, COLOUR_SUCCESS
from ..database import Database
from ..utils import embed
from .logs import send_log

TICKET_TYPES = {
    "support": "الدعم العام",
    "complaint": "شكوى",
    "help": "طلب مساعدة",
    "purchase": "الشراء",
}


async def create_ticket(
    interaction: discord.Interaction, database: Database, ticket_type: str
) -> None:
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("هذا النظام يعمل داخل السيرفر فقط.", ephemeral=True)
        return

    existing = next(
        (
            channel
            for channel in guild.text_channels
            if channel.topic and f"Ticket owner: {interaction.user.id}" in channel.topic
        ),
        None,
    )
    if existing:
        await interaction.response.send_message(f"لديك تذكرة مفتوحة بالفعل: {existing.mention}", ephemeral=True)
        return

    settings = database.get_settings(guild.id)
    category = guild.get_channel(settings["ticket_category_id"]) if settings["ticket_category_id"] else None
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
    }
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            read_message_history=True,
        )

    channel = await guild.create_text_channel(
        name=f"ticket-{interaction.user.name[:16]}-{interaction.user.id % 10000:04d}",
        category=category if isinstance(category, discord.CategoryChannel) else None,
        topic=f"Ticket owner: {interaction.user.id} | type: {ticket_type}",
        overwrites=overwrites,
        reason="فتح تذكرة جديدة",
    )
    card = embed(
        f"تذكرة {TICKET_TYPES.get(ticket_type, 'الدعم')}",
        f"مرحبًا {interaction.user.mention}.\nاكتب تفاصيل طلبك هنا، وسيقوم فريق الإدارة بمساعدتك.\n\n"
        "عند انتهاء الموضوع اضغط زر **إغلاق التذكرة**.",
        COLOUR_PRIMARY,
    )
    await channel.send(embed=card, view=TicketCloseView())
    await interaction.response.send_message(f"تم فتح تذكرتك: {channel.mention}", ephemeral=True)


class TicketTypeSelect(discord.ui.Select):
    def __init__(self, database: Database) -> None:
        options = [
            discord.SelectOption(label=label, value=value, emoji="🎫")
            for value, label in TICKET_TYPES.items()
        ]
        super().__init__(
            placeholder="اختر نوع التذكرة",
            options=options,
            custom_id="alythia:ticket:type",
        )
        self.database = database

    async def callback(self, interaction: discord.Interaction) -> None:
        await create_ticket(interaction, self.database, self.values[0])


class TicketPanelView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect(database))


class TicketCloseView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="إغلاق التذكرة",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="alythia:ticket:close",
    )
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        await interaction.response.send_message(
            "هل أنت متأكد من إغلاق التذكرة؟", view=ConfirmCloseView(), ephemeral=True
        )


class ConfirmCloseView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=30)

    @discord.ui.button(label="نعم، أغلقها", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.edit_message(content="القناة غير موجودة.", view=None)
            return
        await interaction.response.edit_message(content="سيتم حذف التذكرة خلال ثوانٍ...", view=None)
        await interaction.channel.delete(reason=f"إغلاق تذكرة بواسطة {interaction.user}")

    @discord.ui.button(label="إلغاء", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        await interaction.response.edit_message(content="تم إلغاء الإغلاق.", view=None)


class Tickets(commands.Cog):
    ticket = app_commands.Group(name="ticket", description="إدارة نظام التذاكر")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database

    @ticket.command(name="setup", description="إنشاء لوحة فتح التذاكر")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(category="Category اختيارية لقنوات التذاكر")
    async def setup_ticket(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel | None = None,
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("اختر قناة نصية لإرسال لوحة التذاكر.", ephemeral=True)
            return
        if category:
            self.database.set_setting(interaction.guild_id, "ticket_category_id", category.id)
        card = embed(
            "مركز الدعم",
            "هل تحتاج إلى مساعدة؟ اختر نوع التذكرة من القائمة، وسيتم إنشاء قناة خاصة بك وبفريق الإدارة.",
            COLOUR_PRIMARY,
        )
        await interaction.channel.send(embed=card, view=TicketPanelView(self.database))
        await interaction.response.send_message(
            embed=embed("تم إعداد التذاكر", "تم نشر لوحة فتح التذاكر في هذه القناة.", COLOUR_SUCCESS),
            ephemeral=True,
        )


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Tickets(bot, database))
    bot.add_view(TicketPanelView(database))
    bot.add_view(TicketCloseView())
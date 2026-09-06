from __future__ import annotations

import asyncio
import logging
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import discord
from discord import app_commands
from discord.ext import commands

from .config import TOKEN, missing_configuration
from .database import Database
from .cogs import (
    autorole,
    automod,
    custom,
    contact,
    community,
    economy,
    fun,
    general,
    giveaways,
    levels,
    line,
    logs,
    moderation,
    reaction_roles,
    suggestions,
    tickets,
    welcome,
    prefix,
    voice,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("alythia")
STATUS_PATH = Path(__file__).with_name("runtime_status.json")


def verify_token_application(token: str) -> None:
    request = Request(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bot {token}"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            identity = json.loads(response.read().decode("utf-8"))
        logger.info(
            "التوكن مرتبط بالبوت: %s (ID: %s)",
            identity.get("username", "غير معروف"),
            identity.get("id", "غير معروف"),
        )
    except HTTPError as error:
        logger.error("تعذر التحقق من التوكن. رمز Discord: %s", error.code)
    except (URLError, TimeoutError) as error:
        logger.error("تعذر الوصول إلى Discord للتحقق من التوكن: %s", error)


class AlythiaBot(commands.Bot):
    def __init__(self, database: Database) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.database = database
        self._guild_commands_synced = False
        self.command_count = 0
        self._status_task: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        await general.setup(self, self.database)
        await logs.setup(self, self.database)
        await welcome.setup(self, self.database)
        await moderation.setup(self, self.database)
        await autorole.setup(self, self.database)
        await tickets.setup(self, self.database)
        await suggestions.setup(self, self.database)
        await economy.setup(self, self.database)
        await levels.setup(self, self.database)
        await line.setup(self, self.database)
        await community.setup(self, self.database)
        await fun.setup(self, self.database)
        await giveaways.setup(self, self.database)
        await reaction_roles.setup(self, self.database)
        await automod.setup(self, self.database)
        await custom.setup(self, self.database)
        await contact.setup(self, self.database)
        await prefix.setup(self, self.database)
        await voice.setup(self, self.database)
        self.command_count = len(self.tree.get_commands())
        logger.info("تم تحميل %s أمر Slash للمزامنة.", self.command_count)

    def write_runtime_status(self) -> None:
        guilds = []
        for guild in self.guilds:
            settings = self.database.get_settings(guild.id)
            voice_client = guild.voice_client
            guilds.append(
                {
                    "id": str(guild.id),
                    "name": guild.name,
                    "memberCount": guild.member_count or len(guild.members),
                    "voiceConnected": bool(voice_client and voice_client.is_connected()),
                    "voiceChannel": (
                        voice_client.channel.name
                        if voice_client and voice_client.is_connected() and voice_client.channel
                        else None
                    ),
                    "settings": {
                        "welcomeEnabled": settings["welcome_channel_id"] is not None,
                        "logsEnabled": settings["logs_channel_id"] is not None,
                        "automodEnabled": bool(settings["automod_enabled"]),
                        "autoroleConfigured": settings["autorole_id"] is not None,
                        "ticketsConfigured": settings["ticket_category_id"] is not None,
                        "suggestionsConfigured": settings["suggestions_channel_id"] is not None,
                    },
                    "stats": {
                        "warningCount": self.database.warning_count(guild.id),
                        "pendingSuggestionCount": self.database.pending_suggestion_count(guild.id),
                        "economyUserCount": self.database.economy_user_count(guild.id),
                        "levelUserCount": self.database.level_user_count(guild.id),
                    },
                }
            )
        payload = {
            "botOnline": True,
            "botName": self.user.name if self.user else "Alythia",
            "commandCount": self.command_count,
            "updatedAt": datetime.now(UTC).isoformat(),
            "guilds": guilds,
        }
        temporary_path = STATUS_PATH.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_path.replace(STATUS_PATH)

    async def _status_heartbeat(self) -> None:
        while not self.is_closed():
            self.write_runtime_status()
            await asyncio.sleep(30)

    async def on_ready(self) -> None:
        if self.user:
            logger.info("تم تشغيل Alythia باسم %s في %s سيرفر.", self.user, len(self.guilds))
        if self._guild_commands_synced:
            return
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(
                    "تمت مزامنة %s أمرًا مع سيرفر %s.",
                    len(synced),
                    guild.name,
                )
            except discord.HTTPException:
                logger.exception("تعذر مزامنة أوامر السيرفر %s", guild.id)
        # Keep only the guild-scoped copy so Discord does not show every command twice.
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        self._guild_commands_synced = True
        self.write_runtime_status()
        if not self._status_task or self._status_task.done():
            self._status_task = asyncio.create_task(self._status_heartbeat())

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.content.startswith("!"):
            logger.info(
                "تم استقبال أمر بريفكس من %s في %s.",
                message.author,
                message.guild.name if message.guild else "رسائل خاصة",
            )
        await self.process_commands(message)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        original = getattr(error, "original", error)
        if isinstance(error, app_commands.errors.MissingPermissions):
            message = "ليس لديك صلاحية لاستخدام هذا الأمر."
        elif isinstance(original, discord.Forbidden):
            message = "لا أملك الصلاحيات الكافية لتنفيذ هذا الأمر."
        elif isinstance(original, discord.HTTPException):
            message = "حدث خطأ من Discord. تأكد من صلاحيات البوت وحاول مرة أخرى."
        else:
            logger.exception("حدث خطأ في أمر Slash", exc_info=original)
            message = "حدث خطأ غير متوقع. تم تسجيل المشكلة للإدارة."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def on_command_error(
        self, context: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            message = "ليس لديك صلاحية لاستخدام هذا الأمر."
        elif isinstance(error, commands.MissingRequiredArgument):
            message = f"البيانات ناقصة. الاستخدام الصحيح: `!{context.command}` مع كل الخيارات المطلوبة."
        elif isinstance(error, commands.BadArgument):
            message = "البيانات المدخلة غير صحيحة. تأكد من منشن العضو أو كتابة الرقم بشكل صحيح."
        elif isinstance(error, commands.NoPrivateMessage):
            message = "هذا الأمر يعمل داخل السيرفر فقط."
        else:
            logger.exception("حدث خطأ في أمر البريفكس", exc_info=error)
            message = "حدث خطأ غير متوقع أثناء تنفيذ الأمر."
        await context.send(message, delete_after=8)


def main() -> None:
    error = missing_configuration()
    if error:
        raise RuntimeError(error)
    verify_token_application(TOKEN)
    database = Database()
    bot = AlythiaBot(database)
    try:
        bot.run(TOKEN)
    finally:
        database.close()


if __name__ == "__main__":
    main()
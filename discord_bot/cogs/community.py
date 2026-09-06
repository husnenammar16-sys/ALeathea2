from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ..config import (
    COLOUR_PRIMARY,
    COLOUR_SUCCESS,
    COLOUR_WARNING,
    XP_COOLDOWN,
    XP_MIN_MESSAGE_LENGTH,
    XP_REPEAT_WINDOW,
    XP_SPAM_MESSAGE_LIMIT,
    XP_SPAM_WINDOW,
)
from ..database import Database
from ..utils import embed, member_name
from .levels import PageView
from .logs import send_log


def clean_message(content: str) -> str:
    return re.sub(r"\s+", " ", content.casefold()).strip()


def period_keys() -> dict[str, str]:
    now = datetime.now(UTC)
    return {
        "daily": now.date().isoformat(),
        "weekly": now.strftime("%G-W%V"),
    }


class Community(commands.Cog):
    title = app_commands.Group(name="title", description="إدارة الألقاب التي فتحتها")
    event = app_commands.Group(name="event", description="أحداث Alythia العالمية")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database
        self.activity_cooldowns: dict[tuple[int, int], float] = {}
        self.last_messages: dict[tuple[int, int], tuple[float, str]] = {}
        self.recent_messages: defaultdict[tuple[int, int], deque[float]] = defaultdict(
            deque
        )

    def _eligible_activity(self, message: discord.Message) -> bool:
        if not message.guild or message.author.bot:
            return False
        content = clean_message(message.content)
        if len(content) < XP_MIN_MESSAGE_LENGTH:
            return False
        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        recent = self.recent_messages[key]
        while recent and now - recent[0] > XP_SPAM_WINDOW:
            recent.popleft()
        recent.append(now)
        if len(recent) > XP_SPAM_MESSAGE_LIMIT:
            return False
        previous = self.last_messages.get(key)
        if previous and previous[1] == content and now - previous[0] < XP_REPEAT_WINDOW:
            return False
        self.last_messages[key] = (now, content)
        if now - self.activity_cooldowns.get(key, 0) < XP_COOLDOWN:
            return False
        self.activity_cooldowns[key] = now
        return True

    def _unlock_titles(self, guild_id: int, user_id: int) -> list[object]:
        row = self.database.get_level(guild_id, user_id)
        known = {str(title["id"]) for title in self.database.user_titles(guild_id, user_id)}
        unlocked: list[object] = []
        for title in self.database.list_titles():
            if str(title["id"]) in known:
                continue
            value = {
                "level": int(row["level"]),
                "reputation": int(row["reputation"]),
                "quests_completed": int(row["quests_completed"]),
            }.get(str(title["requirement_type"]), 0)
            if value >= int(title["requirement_value"]) and self.database.unlock_title(
                guild_id, user_id, str(title["id"])
            ):
                if not row["current_title_id"]:
                    self.database.set_current_title(guild_id, user_id, str(title["id"]))
                unlocked.append(title)
        return unlocked

    async def _announce_titles(
        self, channel: discord.abc.Messageable, titles: list[object]
    ) -> None:
        for title in titles:
            await channel.send(
                f"🎖️ **Title Unlocked!**\n"
                f"لقد فتحت لقب **{title['name']}**!\n>{title['description']}"
            )

    def _quest_embed(self, guild_id: int, target: discord.Member) -> discord.Embed:
        rows = self.database.quest_rows(guild_id, target.id, period_keys())
        lines: list[str] = []
        for quest in rows:
            status = "✅" if quest["completed"] else "🔄"
            lines.append(
                f"{status} {quest['emoji']} **{quest['name']}** "
                f"({quest['period']})\n> {quest['description']}\n"
                f"> التقدم: **{quest['progress']}/{quest['requirement_value']}** "
                f"• المكافأة: **{quest['xp_reward']} XP**"
            )
        card = embed(
            f"📜 مهام {member_name(target)}",
            "\n\n".join(lines) or "لا توجد مهام متاحة حاليًا.",
            COLOUR_PRIMARY,
        )
        card.set_footer(text="تتقدم المهام تلقائيًا مع نشاطك المؤهل")
        return card

    @app_commands.command(name="quests", description="عرض مهامك اليومية والأسبوعية")
    @app_commands.describe(member="عضو اختياري")
    async def quests(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            await interaction.response.send_message(
                "تعذر تحديد العضو.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=self._quest_embed(interaction.guild_id, target)
        )

    @app_commands.command(name="reputation", description="عرض Reputation لعضو")
    @app_commands.describe(member="عضو اختياري")
    async def reputation(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            await interaction.response.send_message(
                "تعذر تحديد العضو.", ephemeral=True
            )
            return
        value = self.database.reputation(interaction.guild_id, target.id)
        await interaction.response.send_message(
            embed=embed(
                f"🤝 Reputation • {member_name(target)}",
                f"يمتلك هذا العضو **{value}** نقاط Reputation.\n"
                "يمكن للعضو الحصول على نقطة واحدة من كل عضو كل 24 ساعة.",
            )
        )

    @app_commands.command(name="give-rep", description="منح Reputation لعضو")
    @app_commands.describe(member="العضو المستحق", reason="سبب المنح")
    async def give_rep(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        if member.bot or member.id == interaction.user.id:
            await interaction.response.send_message(
                "لا يمكنك منح Reputation لنفسك أو لبوت.", ephemeral=True
            )
            return
        reason = reason.strip()[:300]
        if len(reason) < 3:
            await interaction.response.send_message(
                "اكتب سببًا واضحًا لمنح Reputation.", ephemeral=True
            )
            return
        value = self.database.give_reputation(
            interaction.guild_id, interaction.user.id, member.id, reason
        )
        if value is None:
            await interaction.response.send_message(
                "لقد منحت هذا العضو Reputation خلال آخر 24 ساعة.", ephemeral=True
            )
            return
        unlocked = self._unlock_titles(interaction.guild_id, member.id)
        await interaction.response.send_message(
            f"🤝 تم منح **+1 Reputation** إلى {member.mention}.\n"
            f"السبب: {reason}\nالرصيد الحالي: **{value}**"
        )
        if unlocked:
            await self._announce_titles(interaction.channel, unlocked)

    @app_commands.command(
        name="rep-leaderboard", description="عرض ترتيب Reputation في السيرفر"
    )
    async def rep_leaderboard(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        rows = self.database.reputation_leaderboard(interaction.guild_id, 10)
        lines = [
            f"**{index}.** <@{row['user_id']}> — **{row['reputation']}** Reputation"
            for index, row in enumerate(rows, 1)
        ]
        await interaction.response.send_message(
            embed=embed(
                "🤝 Reputation Leaderboard",
                "\n".join(lines) or "لا توجد Reputation مسجلة بعد.",
            )
        )

    @title.command(name="list", description="عرض الألقاب المكتملة والمقفلة")
    async def title_list(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        target = interaction.user
        owned = {str(row["id"]): row for row in self.database.user_titles(
            interaction.guild_id, target.id
        )}
        current = self.database.current_title(interaction.guild_id, target.id)
        lines = []
        for title in self.database.list_titles():
            status = "✅" if title["id"] in owned else "🔒"
            selected = " • الحالي" if current and current["id"] == title["id"] else ""
            lines.append(
                f"{status} **{title['name']}**{selected}\n"
                f"> {title['description']}"
            )
        await interaction.response.send_message(
            embed=embed(
                f"🎖️ ألقاب {member_name(target)}",
                "\n\n".join(lines),
            )
        )

    @title.command(name="set", description="اختيار لقب من الألقاب التي فتحتها")
    @app_commands.describe(title="اللقب")
    @app_commands.choices(
        title=[
            app_commands.Choice(name="Newcomer", value="newcomer"),
            app_commands.Choice(name="Explorer", value="explorer"),
            app_commands.Choice(name="Respected", value="respected"),
            app_commands.Choice(name="Quester", value="quester"),
            app_commands.Choice(name="Veteran", value="veteran"),
            app_commands.Choice(name="Legend", value="legend"),
        ]
    )
    async def title_set(
        self, interaction: discord.Interaction, title: app_commands.Choice[str]
    ) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        if not self.database.set_current_title(
            interaction.guild_id, interaction.user.id, title.value
        ):
            await interaction.response.send_message(
                "هذا اللقب مقفل. استخدم `/title list` لمعرفة شروط فتحه.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"🎖️ تم اختيار لقبك الحالي: **{title.name}**."
        )

    def _event_embed(self, event: object) -> discord.Embed:
        progress = int(event["progress"])
        goal = int(event["goal"])
        card = embed(
            f"🌍 {event['name']}",
            str(event["description"]),
            COLOUR_SUCCESS if progress >= goal else COLOUR_PRIMARY,
        )
        card.add_field(
            name="التقدم",
            value=f"**{progress:,} / {goal:,}**\n"
            f"{'█' * min(20, round(progress / max(goal, 1) * 20))}"
            f"{'░' * max(0, 20 - min(20, round(progress / max(goal, 1) * 20)))}",
        )
        card.add_field(name="مكافأة المشاركة", value=f"**{event['xp_reward']} XP**")
        card.add_field(
            name="ينتهي",
            value=discord.utils.format_dt(
                datetime.fromisoformat(str(event["ends_at"])), style="R"
            ),
        )
        card.set_footer(text="كل رسالة نشاط مؤهلة تزيد مساهمة المجتمع")
        return card

    @event.command(name="status", description="عرض الحدث العالمي النشط")
    async def event_status(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        current = self.database.active_world_event(interaction.guild_id)
        if current and datetime.fromisoformat(str(current["ends_at"])) <= datetime.now(UTC):
            self.database.end_world_event(interaction.guild_id)
            current = None
        if not current:
            await interaction.response.send_message(
                embed=embed("🌍 World Event", "لا يوجد حدث عالمي نشط حاليًا.")
            )
            return
        await interaction.response.send_message(embed=self._event_embed(current))

    @event.command(name="start", description="بدء حدث عالمي (للإدارة)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        name="اسم الحدث",
        description="وصف الحدث",
        goal="عدد المشاركات المطلوبة",
        reward="مكافأة XP للمشارك الذي يكمل الحدث",
        hours="مدة الحدث بالساعات",
    )
    async def event_start(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str,
        goal: app_commands.Range[int, 1, 1_000_000],
        reward: app_commands.Range[int, 0, 1_000_000],
        hours: app_commands.Range[int, 1, 720],
    ) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        current = self.database.start_world_event(
            interaction.guild_id,
            name.strip()[:100],
            description.strip()[:1000],
            int(goal),
            int(reward),
            (datetime.now(UTC) + timedelta(hours=int(hours))).isoformat(),
            interaction.user.id,
        )
        if not current:
            await interaction.response.send_message(
                "يوجد حدث عالمي نشط بالفعل في هذا السيرفر.", ephemeral=True
            )
            return
        await send_log(
            self.bot,
            self.database,
            interaction.guild,
            "بدء حدث عالمي",
            f"{interaction.user.mention} بدأ حدث **{name}**.",
        )
        await interaction.response.send_message(
            content="🌍 بدأ حدث عالمي جديد!",
            embed=self._event_embed(current),
        )

    @event.command(name="end", description="إنهاء الحدث العالمي (للإدارة)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def event_end(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        current = self.database.end_world_event(interaction.guild_id)
        if not current:
            await interaction.response.send_message(
                "لا يوجد حدث عالمي نشط.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=embed(
                "🌍 تم إنهاء الحدث",
                f"**{current['name']}**\n"
                f"التقدم النهائي: **{current['progress']:,}/{current['goal']:,}**",
                COLOUR_WARNING,
            )
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not self._eligible_activity(message):
            return
        assert message.guild is not None
        guild_id = message.guild.id
        user_id = message.author.id
        completed_quests = self.database.advance_quests(
            guild_id, user_id, period_keys()
        )
        for quest in completed_quests:
            self.database.add_xp(
                guild_id, user_id, int(quest["xp_reward"]), message_count=0
            )
            await message.channel.send(
                f"✅ **Quest Complete!** {message.author.mention}\n"
                f"{quest['emoji']} **{quest['name']}** — "
                f"+{quest['xp_reward']} XP"
            )
        event = self.database.advance_world_event(guild_id)
        if event and not event["active"]:
            self.database.add_xp(
                guild_id, user_id, int(event["xp_reward"]), message_count=0
            )
            await message.channel.send(
                f"🌍 **World Event Complete!**\n"
                f"**{event['name']}** اكتمل! {message.author.mention} حصل على "
                f"**+{event['xp_reward']} XP**."
            )
        unlocked = self._unlock_titles(guild_id, user_id)
        if unlocked:
            await self._announce_titles(message.channel, unlocked)


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Community(bot, database))
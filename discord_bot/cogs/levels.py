from __future__ import annotations

import re
import random
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Sequence

import discord
from discord import app_commands
from discord.ext import commands

from ..config import (
    COLOUR_PRIMARY,
    COLOUR_SUCCESS,
    XP_COOLDOWN,
    XP_MAX,
    XP_MIN,
    XP_MIN_MESSAGE_LENGTH,
    XP_REPEAT_WINDOW,
    XP_SPAM_MESSAGE_LIMIT,
    XP_SPAM_WINDOW,
)
from ..database import Database
from ..utils import embed, member_name
from .logs import send_log


RARITY_COLOURS = {
    "Common": 0x94A3B8,
    "Uncommon": 0x22C55E,
    "Rare": 0x38BDF8,
    "Epic": 0xA855F7,
    "Legendary": 0xF59E0B,
}


def progress_bar(value: int, maximum: int, size: int = 10) -> str:
    if maximum <= 0:
        return "░" * size
    filled = max(0, min(size, round(value / maximum * size)))
    return "█" * filled + "░" * (size - filled)


def clean_message(content: str) -> str:
    return re.sub(r"\s+", " ", content.casefold()).strip()


def profile_embed(database: Database, guild_id: int, target: discord.Member) -> discord.Embed:
    row = database.get_level(
        guild_id,
        target.id,
        target.joined_at.isoformat() if target.joined_at else None,
    )
    level = int(row["level"])
    total_xp = int(row["xp"])
    current_floor = database.xp_for_level(level)
    next_floor = database.xp_for_level(level + 1)
    progress = max(0, total_xp - current_floor)
    span = max(1, next_floor - current_floor)
    rank = database.level_rank(guild_id, target.id)
    achievements = database.achievement_count(guild_id, target.id)
    card = discord.Embed(
        title="👤 ALYTHIA PROFILE",
        description=f"**{member_name(target)}**\n`{target.name}`",
        colour=COLOUR_PRIMARY,
    )
    card.set_thumbnail(url=target.display_avatar.url)
    card.add_field(name="🏆 المستوى", value=f"**Level {level}**", inline=True)
    card.add_field(name="📊 الترتيب", value=f"**#{rank}** في السيرفر", inline=True)
    card.add_field(
        name="✨ XP",
        value=(
            f"{progress_bar(progress, span)}\n"
            f"**{total_xp:,} / {next_floor:,}**"
        ),
        inline=False,
    )
    card.add_field(name="🎖️ الإنجازات", value=f"**{achievements}** مكتملة", inline=True)
    card.add_field(name="💬 الرسائل", value=f"**{int(row['message_count']):,}**", inline=True)
    if row["joined_at"]:
        joined = discord.utils.format_dt(
            datetime.fromisoformat(str(row["joined_at"])), style="D"
        )
        card.add_field(name="📅 انضم للسيرفر", value=joined, inline=True)
    card.set_footer(text="Alythia • ملف العضو")
    return card


class PageView(discord.ui.View):
    def __init__(self, requester_id: int, pages: Sequence[discord.Embed]) -> None:
        super().__init__(timeout=180)
        self.requester_id = requester_id
        self.pages = list(pages)
        self.page = 0
        self.previous.disabled = True
        self.next.disabled = len(self.pages) <= 1

    def update_buttons(self) -> None:
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page >= len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "هذه الأزرار متاحة لصاحب الطلب فقط.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        self.previous.disabled = True
        self.next.disabled = True

    @discord.ui.button(label="السابق", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.page], view=self
        )

    @discord.ui.button(label="التالي", emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.page], view=self
        )


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database
        self.cooldowns: dict[tuple[int, int], float] = {}
        self.last_messages: dict[tuple[int, int], tuple[float, str]] = {}
        self.recent_messages: defaultdict[tuple[int, int], deque[float]] = defaultdict(
            deque
        )

    def _guild_id(self, interaction: discord.Interaction) -> int | None:
        return interaction.guild_id

    def _target(self, interaction: discord.Interaction, member: discord.Member | None) -> discord.Member:
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            raise ValueError("هذا الأمر يعمل داخل السيرفر فقط.")
        return target

    def _new_achievements(self, guild_id: int, user_id: int, row: object) -> list[object]:
        unlocked: list[object] = []
        known = self.database.unlocked_achievement_ids(guild_id, user_id)
        for achievement in self.database.list_achievements():
            if achievement["id"] in known:
                continue
            value = {
                "messages": int(row["message_count"]),
                "level": int(row["level"]),
                "late_night_days": int(row["late_night_days"]),
            }.get(str(achievement["requirement_type"]), 0)
            if value >= int(achievement["requirement_value"]) and self.database.unlock_achievement(
                guild_id, user_id, str(achievement["id"])
            ):
                unlocked.append(achievement)
        return unlocked

    async def _announce_achievements(
        self, channel: discord.abc.Messageable, achievements: Sequence[object]
    ) -> None:
        for achievement in achievements:
            await channel.send(
                f"🏆 **Achievement Unlocked!**\n"
                f"{achievement['emoji']} **{achievement['name']}** — {achievement['rarity']}\n"
                f"{achievement['description']}"
            )

    def _profile_embed(
        self, guild_id: int, target: discord.Member
    ) -> discord.Embed:
        return profile_embed(self.database, guild_id, target)

    async def _send_profile(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None,
    ) -> None:
        guild_id = self._guild_id(interaction)
        if guild_id is None:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        target = self._target(interaction, member)
        await interaction.response.send_message(
            embed=self._profile_embed(guild_id, target)
        )

    @app_commands.command(name="rank", description="عرض مستواك أو مستوى عضو")
    @app_commands.describe(member="عضو اختياري")
    async def rank(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        await self._send_profile(interaction, member)

    @app_commands.command(name="achievements", description="عرض الإنجازات المكتملة والمقفلة")
    @app_commands.describe(member="عضو اختياري")
    async def achievements(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        guild_id = self._guild_id(interaction)
        if guild_id is None:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        target = self._target(interaction, member)
        completed = {
            str(row["id"]): row for row in self.database.user_achievements(guild_id, target.id)
        }
        all_achievements = self.database.list_achievements()
        pages: list[discord.Embed] = []
        page_size = 5
        for start in range(0, len(all_achievements), page_size):
            page_rows = all_achievements[start : start + page_size]
            lines: list[str] = []
            for achievement in page_rows:
                if achievement["id"] in completed:
                    status = "✅"
                    when = discord.utils.format_dt(
                        datetime.fromisoformat(str(completed[achievement["id"]]["unlocked_at"])),
                        style="d",
                    )
                    detail = f"مكتمل {when}"
                else:
                    status = "🔒"
                    detail = achievement["description"]
                lines.append(
                    f"{status} {achievement['emoji']} **{achievement['name']}** "
                    f"— `{achievement['rarity']}`\n> {detail}"
                )
            card = discord.Embed(
                title=f"🎖️ إنجازات {member_name(target)}",
                description="\n\n".join(lines),
                colour=COLOUR_SUCCESS if completed else COLOUR_PRIMARY,
            )
            card.set_footer(
                text=f"مكتملة: {len(completed)}/{len(all_achievements)} • "
                f"صفحة {start // page_size + 1}/{max(1, (len(all_achievements) + page_size - 1) // page_size)}"
            )
            pages.append(card)
        view = PageView(interaction.user.id, pages)
        await interaction.response.send_message(embed=pages[0], view=view)

    @app_commands.command(name="leaderboard", description="عرض ترتيب XP أو المستويات")
    @app_commands.describe(mode="نوع الترتيب")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="XP", value="xp"),
            app_commands.Choice(name="المستوى", value="level"),
        ]
    )
    async def leaderboard(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str] | None = None
    ) -> None:
        guild_id = self._guild_id(interaction)
        if guild_id is None:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return
        sort_mode = mode.value if mode else "xp"
        total = self.database.count_levels(guild_id)
        pages: list[discord.Embed] = []
        page_size = 10
        for offset in range(0, max(total, 1), page_size):
            rows = self.database.level_leaderboard(
                guild_id, page_size, offset, sort_mode
            )
            lines = []
            medals = ("🥇", "🥈", "🥉")
            for index, row in enumerate(rows, start=offset + 1):
                medal = medals[index - 1] if index <= 3 else f"`{index}`"
                lines.append(
                    f"{medal} <@{row['user_id']}> — **Level {row['level']}** "
                    f"• `{int(row['xp']):,} XP`"
                )
            pages.append(
                embed(
                    "🏆 ALYTHIA LEADERBOARD",
                    "\n".join(lines) or "لا توجد بيانات XP بعد.",
                )
            )
            pages[-1].set_footer(
                text=f"الترتيب حسب {'XP' if sort_mode == 'xp' else 'المستوى'} • "
                f"صفحة {offset // page_size + 1}/{max(1, (total + page_size - 1) // page_size)}"
            )
        view = PageView(interaction.user.id, pages)
        await interaction.response.send_message(embed=pages[0], view=view)

    @app_commands.command(name="setlevel", description="تعيين مستوى عضو (للإدارة)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="العضو", level="المستوى الجديد")
    async def setlevel(
        self, interaction: discord.Interaction, member: discord.Member, level: app_commands.Range[int, 1, 1000]
    ) -> None:
        guild_id = self._guild_id(interaction)
        if guild_id is None:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        row = self.database.set_level_values(
            guild_id, member.id, self.database.xp_for_level(level), level
        )
        unlocked = self._new_achievements(guild_id, member.id, row)
        await send_log(
            self.bot,
            self.database,
            interaction.guild,
            "تعديل مستوى يدوي",
            f"{interaction.user.mention} عيّن مستوى {member.mention} إلى **{level}**.",
        )
        await interaction.response.send_message(
            f"تم تعيين مستوى {member.mention} إلى **{level}**.\n"
            f"تم فتح {len(unlocked)} إنجاز جديد.",
            ephemeral=True,
        )

    @app_commands.command(name="addxp", description="إضافة XP لعضو (للإدارة)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="العضو", amount="كمية XP")
    async def addxp(
        self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 1000000]
    ) -> None:
        await self._change_xp(interaction, member, int(amount), "إضافة XP يدوي")

    @app_commands.command(name="removexp", description="إزالة XP من عضو (للإدارة)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="العضو", amount="كمية XP")
    async def removexp(
        self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 1000000]
    ) -> None:
        await self._change_xp(interaction, member, -int(amount), "إزالة XP يدوي")

    async def _change_xp(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
        action: str,
    ) -> None:
        guild_id = self._guild_id(interaction)
        if guild_id is None:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        current = self.database.get_level(guild_id, member.id)
        row = self.database.set_level_values(
            guild_id,
            member.id,
            max(0, int(current["xp"]) + amount),
            self.database.level_for_xp(max(0, int(current["xp"]) + amount)),
        )
        unlocked = self._new_achievements(guild_id, member.id, row)
        await send_log(
            self.bot,
            self.database,
            interaction.guild,
            action,
            f"{interaction.user.mention} عدّل XP للعضو {member.mention} بمقدار **{amount:+,}**.",
        )
        await interaction.response.send_message(
            f"تم تحديث XP للعضو {member.mention} إلى **{int(row['xp']):,}**.",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return
        content = clean_message(message.content)
        if len(content) < XP_MIN_MESSAGE_LENGTH:
            return
        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        recent = self.recent_messages[key]
        while recent and now - recent[0] > XP_SPAM_WINDOW:
            recent.popleft()
        recent.append(now)
        if len(recent) > XP_SPAM_MESSAGE_LIMIT:
            return
        previous = self.last_messages.get(key)
        if previous and previous[1] == content and now - previous[0] < XP_REPEAT_WINDOW:
            return
        self.last_messages[key] = (now, content)
        if now - self.cooldowns.get(key, 0) < XP_COOLDOWN:
            return
        self.cooldowns[key] = now
        joined_at = message.author.joined_at.isoformat() if message.author.joined_at else None
        local_now = datetime.now().astimezone()
        late_night_date = local_now.date().isoformat() if local_now.hour < 6 else None
        before = self.database.get_level(message.guild.id, message.author.id, joined_at)
        after = self.database.add_xp(
            message.guild.id,
            message.author.id,
            random.randint(XP_MIN, XP_MAX),
            message_count=1,
            late_night_date=late_night_date,
            joined_at=joined_at,
        )
        unlocked = self._new_achievements(message.guild.id, message.author.id, after)
        if int(after["level"]) > int(before["level"]):
            await message.channel.send(
                f"🎉 **LEVEL UP!**\nمبروك {message.author.mention}!\n"
                f"🏆 وصلت إلى **Level {after['level']}**\n"
                "استمر بالتفاعل في Alythia!"
            )
        if unlocked:
            await self._announce_achievements(message.channel, unlocked)


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Levels(bot, database))
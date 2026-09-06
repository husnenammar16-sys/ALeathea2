from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..config import COLOUR_DANGER, COLOUR_WARNING
from ..database import Database
from ..utils import embed, member_name
from .logs import send_log


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database

    @app_commands.command(name="ban", description="حظر عضو من السيرفر")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(member="العضو", reason="سبب الحظر")
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "لم يتم تحديد سبب",
    ) -> None:
        await member.ban(reason=reason)
        await interaction.response.send_message(
            embed=embed("تم الحظر", f"تم حظر **{member_name(member)}**.\nالسبب: {reason}", COLOUR_DANGER)
        )
        await send_log(self.bot, self.database, interaction.guild, "حظر عضو", f"{member} — {reason}", COLOUR_DANGER)

    @app_commands.command(name="kick", description="طرد عضو من السيرفر")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(member="العضو", reason="سبب الطرد")
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "لم يتم تحديد سبب",
    ) -> None:
        await member.kick(reason=reason)
        await interaction.response.send_message(
            embed=embed("تم الطرد", f"تم طرد **{member_name(member)}**.\nالسبب: {reason}", COLOUR_WARNING)
        )
        await send_log(self.bot, self.database, interaction.guild, "طرد عضو", f"{member} — {reason}", COLOUR_WARNING)

    @app_commands.command(name="timeout", description="تقييد عضو لمدة محددة")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="العضو", minutes="المدة بالدقائق", reason="السبب")
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "مخالفة قوانين السيرفر",
    ) -> None:
        await member.timeout(minutes * 60, reason=reason)
        await interaction.response.send_message(
            embed=embed("تم التقييد", f"تم تقييد {member.mention} لمدة **{minutes} دقيقة**.\nالسبب: {reason}", COLOUR_WARNING)
        )
        await send_log(self.bot, self.database, interaction.guild, "تقييد عضو", f"{member} — {reason}", COLOUR_WARNING)

    @app_commands.command(name="untimeout", description="إزالة تقييد عضو")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="العضو")
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await member.timeout(None, reason=f"إزالة التقييد بواسطة {interaction.user}")
        await interaction.response.send_message(
            embed=embed("تمت إزالة التقييد", f"يمكن لـ {member.mention} التحدث الآن.")
        )

    @app_commands.command(name="warn", description="تسجيل تحذير على عضو")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(member="العضو", reason="سبب التحذير")
    async def warn(
        self, interaction: discord.Interaction, member: discord.Member, reason: str
    ) -> None:
        warning_id = self.database.add_warning(
            interaction.guild_id, member.id, interaction.user.id, reason
        )
        total = len(self.database.list_warnings(interaction.guild_id, member.id))
        try:
            await member.send(
                embed=embed(
                    "تنبيه من إدارة السيرفر",
                    f"تم تحذيرك في **{interaction.guild.name}**.\nالسبب: {reason}\nعدد تحذيراتك: **{total}**",
                    COLOUR_WARNING,
                )
            )
        except discord.HTTPException:
            pass
        await interaction.response.send_message(
            embed=embed(
                "تم تسجيل التحذير",
                f"تم تحذير {member.mention}.\nالسبب: {reason}\nعدد التحذيرات: **{total}**\nرقم التحذير: `{warning_id}`",
                COLOUR_WARNING,
            )
        )
        await send_log(
            self.bot,
            self.database,
            interaction.guild,
            "تحذير عضو",
            f"{member.mention}\nالسبب: {reason}\nبواسطة: {interaction.user.mention}",
            COLOUR_WARNING,
        )

    @app_commands.command(name="warnings", description="عرض تحذيرات عضو")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(member="العضو")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        rows = self.database.list_warnings(interaction.guild_id, member.id)
        if not rows:
            await interaction.response.send_message(
                embed=embed("سجل التحذيرات", f"لا توجد تحذيرات مسجلة على {member.mention}."), ephemeral=True
            )
            return
        lines = [
            f"`#{row['id']}` — {row['reason']} (<t:{int(discord.utils.parse_time(row['created_at']).timestamp())}:R>)"
            for row in rows[:15]
        ]
        await interaction.response.send_message(
            embed=embed(f"تحذيرات {member_name(member)}", "\n".join(lines)), ephemeral=True
        )

    @app_commands.command(name="clearwarnings", description="حذف تحذيرات عضو")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="العضو")
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        count = self.database.clear_warnings(interaction.guild_id, member.id)
        await interaction.response.send_message(
            embed=embed("تم حذف التحذيرات", f"تم حذف **{count}** تحذيرًا عن {member.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear", description="حذف رسائل من القناة")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(amount="عدد الرسائل من 1 إلى 100")
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("هذا الأمر يعمل في القنوات النصية فقط.", ephemeral=True)
            return
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(
            embed=embed("تم التنظيف", f"تم حذف **{len(deleted)}** رسالة.", COLOUR_WARNING), ephemeral=True
        )

    @app_commands.command(name="lock", description="قفل القناة الحالية")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("هذا الأمر يعمل في القنوات النصية فقط.", ephemeral=True)
            return
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            send_messages=False,
            reason=f"قفل بواسطة {interaction.user}",
        )
        await interaction.response.send_message(embed=embed("تم قفل القناة", "لا يمكن للأعضاء إرسال رسائل حاليًا."))

    @app_commands.command(name="unlock", description="فتح القناة الحالية")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("هذا الأمر يعمل في القنوات النصية فقط.", ephemeral=True)
            return
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            send_messages=None,
            reason=f"فتح بواسطة {interaction.user}",
        )
        await interaction.response.send_message(embed=embed("تم فتح القناة", "يمكن للأعضاء إرسال الرسائل الآن."))


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Moderation(bot, database))
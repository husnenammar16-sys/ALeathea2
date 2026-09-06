from __future__ import annotations

import random
import time

import discord
from discord.ext import commands

from ..database import Database
from ..utils import embed, member_name


class PrefixCommands(commands.Cog):
    """أوامر الدردشة التي تبدأ بالبريفكس !."""

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.database = database

    @commands.command(name="help")
    async def prefix_help(self, ctx: commands.Context[commands.Bot]) -> None:
        await ctx.send(
            embed=embed(
                "أوامر Alythia بالبريفكس !",
                "**متاحة لكل الأعضاء**\n"
                "`!help` `!ping` `!server` `!user` `!avatar`\n"
                "`!balance` `!daily` `!work` `!pay` `!rich` `!profile`\n"
                "`!rank` `!leaderboard`\n"
                "`!embed الرسالة` لإرسال رسالة على شكل Embed (للإدارة)\n"
                "`!coinflip` `!roll` `!8ball` `!choose`\n"
                "\n**للإدارة فقط**\n"
                "`!warn` `!warnings` `!clearwarnings`\n"
                "`!clear` `!timeout` `!untimeout` `!ban` `!kick`\n\n"
                "`!call` أو `!نداء` لإرسال رسالة خاصة لعضو.\n\n"
                "`!join` أو `!دخول` للبقاء في الروم الصوتي بشكل دائم، و`!leave` للخروج.\n\n"
                "إعداد التذاكر والسحوبات والرتب التفاعلية متاح من أوامر Slash."
            )
        )

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context[commands.Bot]) -> None:
        await ctx.send(embed=embed("سرعة الاستجابة", f"زمن الاستجابة: **{round(self.bot_latency(ctx) * 1000)}ms**"))

    @staticmethod
    def bot_latency(ctx: commands.Context[commands.Bot]) -> float:
        return ctx.bot.latency

    @commands.command(name="server")
    @commands.guild_only()
    async def server(self, ctx: commands.Context[commands.Bot]) -> None:
        guild = ctx.guild
        if not guild:
            return
        card = embed(
            f"معلومات {guild.name}",
            f"المالك: <@{guild.owner_id}>\nالأعضاء: **{guild.member_count}**\nالقنوات: **{len(guild.channels)}**",
        )
        if guild.icon:
            card.set_thumbnail(url=guild.icon.url)
        await ctx.send(embed=card)

    @commands.command(name="user")
    @commands.guild_only()
    async def user(self, ctx: commands.Context[commands.Bot], member: discord.Member | None = None) -> None:
        target = member or ctx.author
        await ctx.send(
            embed=embed(
                f"معلومات {member_name(target)}",
                f"المعرّف: `{target.id}`\nتاريخ الانضمام: {discord.utils.format_dt(target.joined_at, style='D')}",
            )
        )

    @commands.command(name="avatar")
    async def avatar(self, ctx: commands.Context[commands.Bot], member: discord.Member | None = None) -> None:
        target = member or ctx.author
        card = embed(f"صورة {member_name(target)}")
        card.set_image(url=target.display_avatar.url)
        await ctx.send(embed=card)

    @commands.command(name="balance")
    @commands.guild_only()
    async def balance(self, ctx: commands.Context[commands.Bot], member: discord.Member | None = None) -> None:
        target = member or ctx.author
        row = self.database.get_economy(ctx.guild.id, target.id)
        await ctx.send(embed=embed("الرصيد", f"رصيد **{member_name(target)}** هو **{row['balance']:,}** عملة."))

    @commands.command(name="daily")
    @commands.guild_only()
    async def daily(self, ctx: commands.Context[commands.Bot]) -> None:
        row = self.database.get_economy(ctx.guild.id, ctx.author.id)
        if row["last_daily"] and time.time() - discord.utils.parse_time(row["last_daily"]).timestamp() < 86400:
            await ctx.send("استلمت مكافأتك اليومية مسبقًا. حاول غدًا.", delete_after=8)
            return
        amount = random.randint(150, 300)
        balance = self.database.change_balance(ctx.guild.id, ctx.author.id, amount)
        self.database.set_economy_date(ctx.guild.id, ctx.author.id, "last_daily", discord.utils.utcnow().isoformat())
        await ctx.send(embed=embed("المكافأة اليومية", f"حصلت على **{amount}** عملة.\nرصيدك: **{balance:,}**."))

    @commands.command(name="work")
    @commands.guild_only()
    async def work(self, ctx: commands.Context[commands.Bot]) -> None:
        amount = random.randint(40, 120)
        balance = self.database.change_balance(ctx.guild.id, ctx.author.id, amount)
        self.database.set_economy_date(ctx.guild.id, ctx.author.id, "last_work", discord.utils.utcnow().isoformat())
        await ctx.send(embed=embed("تم إنجاز العمل", f"حصلت على **{amount}** عملة.\nرصيدك: **{balance:,}**."))

    @commands.command(name="pay")
    @commands.guild_only()
    async def pay(self, ctx: commands.Context[commands.Bot], member: discord.Member, amount: int) -> None:
        if amount <= 0 or member.bot or member.id == ctx.author.id:
            await ctx.send("اكتب مبلغًا صحيحًا واختر عضوًا آخر.", delete_after=8)
            return
        sender = self.database.get_economy(ctx.guild.id, ctx.author.id)
        if sender["balance"] < amount:
            await ctx.send("رصيدك لا يكفي.", delete_after=8)
            return
        self.database.change_balance(ctx.guild.id, ctx.author.id, -amount)
        self.database.change_balance(ctx.guild.id, member.id, amount)
        await ctx.send(f"تم تحويل **{amount:,}** عملة إلى {member.mention}.")

    @commands.command(name="rich")
    @commands.guild_only()
    async def rich(self, ctx: commands.Context[commands.Bot]) -> None:
        rows = self.database.economy_leaderboard(ctx.guild.id)
        lines = [f"**{i}.** <@{row['user_id']}> — {row['balance']:,} عملة" for i, row in enumerate(rows, 1)]
        await ctx.send(embed=embed("أغنى أعضاء السيرفر", "\n".join(lines) or "لا توجد أرصدة بعد."))

    @commands.command(name="profile")
    @commands.guild_only()
    async def profile(self, ctx: commands.Context[commands.Bot], member: discord.Member | None = None) -> None:
        target = member or ctx.author
        money = self.database.get_economy(ctx.guild.id, target.id)
        level = self.database.get_level(ctx.guild.id, target.id)
        await ctx.send(
            embed=embed(
                f"ملف {member_name(target)}",
                f"المستوى: **{level['level']}**\nالخبرة: **{level['xp']}**\nالرصيد: **{money['balance']:,}**",
            )
        )

    @commands.command(name="rank")
    @commands.guild_only()
    async def rank(self, ctx: commands.Context[commands.Bot], member: discord.Member | None = None) -> None:
        target = member or ctx.author
        row = self.database.get_level(ctx.guild.id, target.id)
        needed = (int(row["level"]) + 1) * 100
        await ctx.send(embed=embed(f"مستوى {member_name(target)}", f"المستوى: **{row['level']}**\nXP: **{row['xp']} / {needed}**"))

    @commands.command(name="leaderboard")
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context[commands.Bot]) -> None:
        rows = self.database.level_leaderboard(ctx.guild.id)
        lines = [f"**{i}.** <@{row['user_id']}> — المستوى {row['level']} ({row['xp']} XP)" for i, row in enumerate(rows, 1)]
        await ctx.send(embed=embed("ترتيب المستويات", "\n".join(lines) or "لا توجد مستويات بعد."))

    @commands.command(name="coinflip")
    async def coinflip(self, ctx: commands.Context[commands.Bot]) -> None:
        await ctx.send(embed=embed("رمي العملة", f"النتيجة: **{random.choice(['صورة', 'كتابة'])}**"))

    @commands.command(name="roll")
    async def roll(self, ctx: commands.Context[commands.Bot], sides: int = 6) -> None:
        if not 2 <= sides <= 100:
            await ctx.send("عدد الأوجه يجب أن يكون بين 2 و100.", delete_after=8)
            return
        await ctx.send(embed=embed("رمي النرد", f"النتيجة: **{random.randint(1, sides)}** من {sides}"))

    @commands.command(name="8ball")
    async def eightball(self, ctx: commands.Context[commands.Bot], *, question: str) -> None:
        answers = ["نعم بالتأكيد.", "على الأغلب نعم.", "لا أظن ذلك.", "الوقت سيكشف الإجابة.", "اسألني لاحقًا."]
        await ctx.send(embed=embed("الكرة السحرية", f"**السؤال:** {question}\n\n**الإجابة:** {random.choice(answers)}"))

    @commands.command(name="choose")
    async def choose(self, ctx: commands.Context[commands.Bot], *, options: str) -> None:
        values = [value.strip() for value in options.split("|") if value.strip()]
        if len(values) < 2:
            await ctx.send("افصل خيارين على الأقل بعلامة `|`.", delete_after=8)
            return
        await ctx.send(embed=embed("الاختيار", f"أختار: **{random.choice(values)}**"))

    @commands.command(name="clear")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context[commands.Bot], amount: int) -> None:
        if not isinstance(ctx.channel, discord.TextChannel):
            return
        deleted = await ctx.channel.purge(limit=max(1, min(amount, 100)) + 1)
        await ctx.send(embed=embed("تم التنظيف", f"تم حذف **{len(deleted) - 1}** رسالة."), delete_after=5)

    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context[commands.Bot], member: discord.Member, *, reason: str = "لم يتم تحديد سبب") -> None:
        await member.ban(reason=reason)
        await ctx.send(embed=embed("تم الحظر", f"تم حظر **{member_name(member)}**.\nالسبب: {reason}"))

    @commands.command(name="kick")
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context[commands.Bot], member: discord.Member, *, reason: str = "لم يتم تحديد سبب") -> None:
        await member.kick(reason=reason)
        await ctx.send(embed=embed("تم الطرد", f"تم طرد **{member_name(member)}**.\nالسبب: {reason}"))

    @commands.command(name="timeout")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context[commands.Bot], member: discord.Member, minutes: int, *, reason: str = "مخالفة قوانين السيرفر") -> None:
        await member.timeout(max(1, min(minutes, 40320)) * 60, reason=reason)
        await ctx.send(embed=embed("تم التقييد", f"تم تقييد {member.mention} لمدة **{minutes} دقيقة**.\nالسبب: {reason}"))

    @commands.command(name="untimeout")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context[commands.Bot], member: discord.Member) -> None:
        await member.timeout(None, reason=f"إزالة التقييد بواسطة {ctx.author}")
        await ctx.send(f"تمت إزالة التقييد عن {member.mention}.")

    @commands.command(name="warn")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context[commands.Bot], member: discord.Member, *, reason: str) -> None:
        self.database.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        total = len(self.database.list_warnings(ctx.guild.id, member.id))
        await ctx.send(embed=embed("تم تسجيل التحذير", f"تم تحذير {member.mention}.\nالعدد: **{total}**\nالسبب: {reason}"))

    @commands.command(name="warnings")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx: commands.Context[commands.Bot], member: discord.Member) -> None:
        rows = self.database.list_warnings(ctx.guild.id, member.id)
        lines = [f"`#{row['id']}` — {row['reason']}" for row in rows[:15]]
        await ctx.send(embed=embed(f"تحذيرات {member_name(member)}", "\n".join(lines) or "لا توجد تحذيرات."))

    @commands.command(name="clearwarnings")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def clearwarnings(self, ctx: commands.Context[commands.Bot], member: discord.Member) -> None:
        count = self.database.clear_warnings(ctx.guild.id, member.id)
        await ctx.send(f"تم حذف **{count}** تحذيرًا عن {member.mention}.")

    @commands.command(name="lock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context[commands.Bot]) -> None:
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False, reason=f"قفل بواسطة {ctx.author}")
            await ctx.send("تم قفل القناة.")

    @commands.command(name="unlock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context[commands.Bot]) -> None:
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None, reason=f"فتح بواسطة {ctx.author}")
            await ctx.send("تم فتح القناة.")


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(PrefixCommands(bot, database))
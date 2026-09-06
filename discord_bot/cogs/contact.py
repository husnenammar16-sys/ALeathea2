from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..config import COLOUR_PRIMARY
from ..utils import embed, member_name


class Contact(commands.Cog):
    def __init__(self, bot: commands.Bot, database: object) -> None:
        pass

    @app_commands.command(name="call", description="إرسال نداء خاص إلى عضو")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(member="العضو الذي سيستلم الرسالة", message="نص النداء")
    async def call(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        message: app_commands.Range[str, 1, 1500],
    ) -> None:
        if member.bot:
            await interaction.response.send_message("لا يمكن إرسال نداء إلى بوت.", ephemeral=True)
            return
        if not interaction.guild:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        card = embed(
            f"نداء من {interaction.guild.name}",
            str(message),
            COLOUR_PRIMARY,
        )
        if interaction.guild.icon:
            card.set_author(
                name=f"من إدارة {interaction.guild.name}",
                icon_url=interaction.guild.icon.url,
            )
        else:
            card.set_author(name=f"من إدارة {interaction.guild.name}")
        card.set_footer(text=f"تم الإرسال بواسطة {member_name(interaction.user)}")
        try:
            await member.send(embed=card)
        except discord.Forbidden:
            await interaction.response.send_message(
                f"تعذر إرسال الرسالة إلى {member.mention}؛ الخاص مغلق أو يمنع الرسائل.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"تم إرسال النداء إلى {member.mention} في الخاص.", ephemeral=True
        )

    @commands.command(name="call", aliases=["نداء"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_call(
        self,
        ctx: commands.Context[commands.Bot],
        member: discord.Member,
        *,
        message: str,
    ) -> None:
        if member.bot:
            await ctx.send("لا يمكن إرسال نداء إلى بوت.", delete_after=8)
            return
        card = embed(
            f"نداء من {ctx.guild.name}",
            message[:1500],
            COLOUR_PRIMARY,
        )
        if ctx.guild.icon:
            card.set_author(name=f"من إدارة {ctx.guild.name}", icon_url=ctx.guild.icon.url)
        else:
            card.set_author(name=f"من إدارة {ctx.guild.name}")
        card.set_footer(text=f"تم الإرسال بواسطة {member_name(ctx.author)}")
        try:
            await member.send(embed=card)
        except discord.Forbidden:
            await ctx.send(
                f"تعذر إرسال الرسالة إلى {member.mention}؛ الخاص مغلق أو يمنع الرسائل.",
                delete_after=8,
            )
            return
        await ctx.send(f"تم إرسال النداء إلى {member.mention} في الخاص.", delete_after=8)


async def setup(bot: commands.Bot, database: object) -> None:
    await bot.add_cog(Contact(bot, database))
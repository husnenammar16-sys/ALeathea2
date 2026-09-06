from __future__ import annotations

from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from ..utils import embed

class Voice(commands.Cog):
    voice = app_commands.Group(name="voice", description="التحكم بوجود البوت في الروم الصوتي")

    def __init__(self, bot: commands.Bot, database: object) -> None:
        self.bot = bot

    async def _join_channel(
        self, guild: discord.Guild, channel: discord.abc.GuildChannel
    ) -> discord.VoiceClient:
        if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            raise ValueError("ليس هذا رومًا صوتيًا.")
        current = guild.voice_client
        if current and current.is_connected():
            if current.channel != channel:
                await current.move_to(channel)
            voice_client = current
        else:
            voice_client = cast(discord.VoiceClient, await channel.connect())
        write_status = getattr(self.bot, "write_runtime_status", None)
        if write_status:
            write_status()
        return voice_client

    async def _leave_guild(self, guild: discord.Guild) -> bool:
        if not guild.voice_client:
            return False
        await guild.voice_client.disconnect(force=True)
        write_status = getattr(self.bot, "write_runtime_status", None)
        if write_status:
            write_status()
        return True

    @voice.command(name="join", description="إدخال البوت إلى رومك الصوتي حتى إخراجه يدويًا")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def join(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "ادخل رومًا صوتيًا أولًا ثم استخدم الأمر.",
                ephemeral=True,
            )
            return
        try:
            voice_client = await self._join_channel(
                interaction.guild,
                interaction.user.voice.channel,
            )
        except (
            discord.ClientException,
            discord.Forbidden,
            discord.HTTPException,
            RuntimeError,
            ValueError,
        ):
            await interaction.response.send_message(
                "تعذر دخول الروم الصوتي. تأكد أن لدي صلاحية **Connect** في الروم.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=embed(
                "تم دخول الروم الصوتي",
                f"دخلت إلى **{voice_client.channel.name}** وسأبقى فيه بشكل دائم.\n"
                "استخدم `/voice leave` لإخراجي قبل انتهاء المدة.",
            ),
            ephemeral=True,
        )

    @voice.command(name="leave", description="إخراج البوت من الروم الصوتي")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def leave(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
            return
        left = await self._leave_guild(interaction.guild)
        await interaction.response.send_message(
            "خرجت من الروم الصوتي." if left else "أنا لست داخل روم صوتي حاليًا.",
            ephemeral=True,
        )

    @commands.command(name="join", aliases=["دخول"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_join(self, ctx: commands.Context[commands.Bot]) -> None:
        if not isinstance(ctx.author, discord.Member) or not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("ادخل رومًا صوتيًا أولًا ثم استخدم `!join`.", delete_after=8)
            return
        try:
            voice_client = await self._join_channel(ctx.guild, ctx.author.voice.channel)
        except (
            discord.ClientException,
            discord.Forbidden,
            discord.HTTPException,
            RuntimeError,
            ValueError,
        ):
            await ctx.send("تعذر دخول الروم. تأكد أن لدي صلاحية Connect.", delete_after=8)
            return
        await ctx.send(
            embed=embed(
                "تم دخول الروم الصوتي",
                f"دخلت إلى **{voice_client.channel.name}** وسأبقى فيه بشكل دائم.",
            )
        )

    @commands.command(name="leave", aliases=["خروج"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_leave(self, ctx: commands.Context[commands.Bot]) -> None:
        left = await self._leave_guild(ctx.guild)
        await ctx.send("خرجت من الروم الصوتي." if left else "أنا لست داخل روم صوتي حاليًا.", delete_after=8)

async def setup(bot: commands.Bot, database: object) -> None:
    await bot.add_cog(Voice(bot, database))
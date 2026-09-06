from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..database import Database
from ..utils import embed


class ReactionRoles(commands.Cog):
    reactionrole = app_commands.Group(name="reactionrole", description="إدارة الرتب التفاعلية")

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database

    @reactionrole.command(name="setup", description="إنشاء رتبة تفاعلية")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(role="الرتبة", emoji="الإيموجي الذي سيضغطه العضو")
    async def setup_role(
        self, interaction: discord.Interaction, role: discord.Role, emoji: str
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("هذا الأمر يعمل في قناة نصية فقط.", ephemeral=True)
            return
        card = embed(
            "رتبة تفاعلية",
            f"اضغط {emoji} للحصول على رتبة {role.mention} أو اضغطه مرة أخرى لإزالتها.",
        )
        message = await interaction.channel.send(embed=card)
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await message.delete()
            await interaction.response.send_message("الإيموجي غير صالح.", ephemeral=True)
            return
        self.database.add_reaction_role(interaction.guild_id, message.id, role.id, emoji)
        await interaction.response.send_message("تم إنشاء الرتبة التفاعلية.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self.update_role(payload, True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self.update_role(payload, False)

    async def update_role(self, payload: discord.RawReactionActionEvent, add: bool) -> None:
        if not payload.guild_id or payload.user_id == self.bot.user.id:
            return
        row = self.database.reaction_role(payload.message_id, str(payload.emoji))
        if not row:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(row["role_id"])
        if not member or not role:
            return
        try:
            if add:
                await member.add_roles(role, reason="رتبة تفاعلية")
            else:
                await member.remove_roles(role, reason="إزالة رتبة تفاعلية")
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(ReactionRoles(bot, database))
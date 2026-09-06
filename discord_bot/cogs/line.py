from __future__ import annotations

from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from ..database import Database


MAX_LINE_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
}


class Line(commands.Cog):
    setup_group = app_commands.Group(name="setup", description="إعدادات السيرفر")
    un_group = app_commands.Group(name="un", description="إزالة إعداد من السيرفر")
    un_setup_group = app_commands.Group(
        name="setup",
        description="إزالة إعداد",
        parent=un_group,
    )

    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.database = database
        self.image_directory = Path(__file__).resolve().parents[1] / "line_images"
        self.image_directory.mkdir(parents=True, exist_ok=True)

    @setup_group.command(name="line", description="تحديد صورة أمر !خط")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(image="الصورة التي سيرسلها البوت عند كتابة !خط")
    async def setup_line(
        self, interaction: discord.Interaction, image: discord.Attachment
    ) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return

        extension = Path(image.filename).suffix.lower()
        content_type = (image.content_type or "").lower()
        if extension not in ALLOWED_EXTENSIONS or (
            content_type and content_type not in ALLOWED_CONTENT_TYPES
        ):
            await interaction.response.send_message(
                "أرفق صورة بصيغة PNG أو JPG أو JPEG أو GIF أو WEBP.",
                ephemeral=True,
            )
            return
        if image.size > MAX_LINE_IMAGE_BYTES:
            await interaction.response.send_message(
                "حجم الصورة كبير جدًا. الحد الأقصى هو 10MB.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            data = await image.read()
        except discord.HTTPException:
            await interaction.followup.send(
                "تعذر تحميل الصورة من Discord. حاول إرفاقها مرة أخرى.",
                ephemeral=True,
            )
            return

        if len(data) > MAX_LINE_IMAGE_BYTES:
            await interaction.followup.send(
                "حجم الصورة كبير جدًا. الحد الأقصى هو 10MB.",
                ephemeral=True,
            )
            return

        target = self.image_directory / f"{interaction.guild_id}{extension}"
        temporary = self.image_directory / f".{interaction.guild_id}.tmp"
        old = self.database.line_image(interaction.guild_id)
        try:
            temporary.write_bytes(data)
            temporary.replace(target)
            self.database.set_line_image(interaction.guild_id, str(target))
        except OSError:
            temporary.unlink(missing_ok=True)
            await interaction.followup.send(
                "تعذر حفظ الصورة على الخادم. حاول مرة أخرى.",
                ephemeral=True,
            )
            return

        if old and old["image_path"] != str(target):
            Path(old["image_path"]).unlink(missing_ok=True)
        await interaction.followup.send(
            "تم إعداد صورة الخط بنجاح. استخدم `!خط` لإرسالها.",
            ephemeral=True,
        )

    @un_setup_group.command(name="line", description="إزالة صورة أمر !خط")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unset_line(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True
            )
            return

        row = self.database.delete_line_image(interaction.guild_id)
        if not row:
            await interaction.response.send_message(
                "لا توجد صورة خط معدة في هذا السيرفر.", ephemeral=True
            )
            return
        Path(row["image_path"]).unlink(missing_ok=True)
        await interaction.response.send_message(
            "تمت إزالة صورة الخط. لن يرسل `!خط` صورة حتى يتم إعدادها من جديد.",
            ephemeral=True,
        )

    @commands.command(name="خط")
    @commands.guild_only()
    async def send_line(self, ctx: commands.Context[commands.Bot]) -> None:
        if not ctx.guild:
            return
        row = self.database.line_image(ctx.guild.id)
        if not row:
            await ctx.send("لم يتم إعداد صورة الخط بعد. استخدم `/setup line` أولًا.")
            return

        image_path = Path(row["image_path"])
        if not image_path.is_file():
            await ctx.send(
                "صورة الخط غير موجودة حاليًا على الخادم. استخدم `/setup line` لإعدادها من جديد."
            )
            return
        await ctx.send(file=discord.File(image_path, filename=image_path.name))


async def setup(bot: commands.Bot, database: Database) -> None:
    await bot.add_cog(Line(bot, database))
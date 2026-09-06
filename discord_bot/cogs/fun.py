from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from ..utils import embed


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot, database: object) -> None:
        pass

    @app_commands.command(name="coinflip", description="رمي عملة")
    async def coinflip(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=embed("رمي العملة", f"النتيجة: **{random.choice(['صورة', 'كتابة'])}**"))

    @app_commands.command(name="roll", description="رمي حجر النرد")
    @app_commands.describe(sides="عدد الأوجه من 2 إلى 100")
    async def roll(self, interaction: discord.Interaction, sides: app_commands.Range[int, 2, 100] = 6) -> None:
        await interaction.response.send_message(embed=embed("رمي النرد", f"النتيجة: **{random.randint(1, sides)}** من {sides}"))

    @app_commands.command(name="eightball", description="اسأل الكرة السحرية")
    @app_commands.describe(question="اكتب سؤالك")
    async def eightball(self, interaction: discord.Interaction, question: str) -> None:
        answers = ["نعم بالتأكيد.", "على الأغلب نعم.", "لا أظن ذلك.", "الوقت سيكشف الإجابة.", "اسألني لاحقًا."]
        await interaction.response.send_message(embed=embed("الكرة السحرية", f"**السؤال:** {question}\n\n**الإجابة:** {random.choice(answers)}"))

    @app_commands.command(name="choose", description="اختيار عشوائي بين خيارات")
    @app_commands.describe(options="افصل الخيارات بعلامة |")
    async def choose(self, interaction: discord.Interaction, options: str) -> None:
        values = [value.strip() for value in options.split("|") if value.strip()]
        if len(values) < 2:
            await interaction.response.send_message("اكتب خيارين على الأقل وافصل بينهما بعلامة `|`.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed("الاختيار", f"أختار: **{random.choice(values)}**"))


async def setup(bot: commands.Bot, database: object) -> None:
    await bot.add_cog(Fun(bot, database))
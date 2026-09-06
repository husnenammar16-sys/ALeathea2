import os


TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DATABASE_PATH = os.getenv("DATABASE_PATH", "discord_bot/alythia.sqlite3")
BOT_NAME = "Alythia"

COLOUR_PRIMARY = 0x8B5CF6
COLOUR_SUCCESS = 0x22C55E
COLOUR_WARNING = 0xF59E0B
COLOUR_DANGER = 0xEF4444
COLOUR_MUTED = 0x64748B

# Member progression settings. Keep these values centralized so the balance can
# be tuned without hunting through the Cog or database code.
XP_MIN = 10
XP_MAX = 20
XP_COOLDOWN = 60
XP_MIN_MESSAGE_LENGTH = 5
XP_REPEAT_WINDOW = 120
XP_SPAM_WINDOW = 10
XP_SPAM_MESSAGE_LIMIT = 5

# Total XP required to reach a level. This produces 100, 250, 450, 700, ...
# for levels 1-4 while preserving a useful progression curve.
LEVEL_BASE_XP = 100
LEVEL_GROWTH_XP = 50


def missing_configuration() -> str | None:
    if not TOKEN:
        return "السر DISCORD_BOT_TOKEN غير موجود في Replit Secrets."
    return None
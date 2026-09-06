from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATABASE_PATH


class Database:
    def __init__(self, path: str = DATABASE_PATH) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                logs_channel_id INTEGER,
                ticket_category_id INTEGER,
                autorole_id INTEGER,
                suggestions_channel_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                message_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS economy (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0,
                last_daily TEXT,
                last_work TEXT,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS levels (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                message_count INTEGER NOT NULL DEFAULT 0,
                joined_at TEXT,
                late_night_days INTEGER NOT NULL DEFAULT 0,
                last_late_night_date TEXT,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                emoji TEXT NOT NULL,
                requirement_type TEXT NOT NULL,
                requirement_value INTEGER NOT NULL,
                rarity TEXT NOT NULL,
                reward TEXT
            );
            CREATE TABLE IF NOT EXISTS user_achievements (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id, achievement_id),
                FOREIGN KEY (achievement_id) REFERENCES achievements(id)
            );
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                prize TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                ended INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (giveaway_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS reaction_roles (
                guild_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                PRIMARY KEY (message_id, emoji)
            );
            CREATE TABLE IF NOT EXISTS custom_commands (
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                response TEXT NOT NULL,
                PRIMARY KEY (guild_id, name)
            );
            """
        )
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(guild_settings)")
        }
        if "automod_enabled" not in columns:
            self.connection.execute(
                "ALTER TABLE guild_settings ADD COLUMN automod_enabled INTEGER NOT NULL DEFAULT 0"
            )
        level_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(levels)")
        }
        level_migrations = {
            "message_count": "INTEGER NOT NULL DEFAULT 0",
            "joined_at": "TEXT",
            "late_night_days": "INTEGER NOT NULL DEFAULT 0",
            "last_late_night_date": "TEXT",
        }
        for column, definition in level_migrations.items():
            if column not in level_columns:
                self.connection.execute(
                    f"ALTER TABLE levels ADD COLUMN {column} {definition}"
                )
        # The previous levels Cog used level 0 and stored progress within the
        # current level. New progression is total-XP based and starts at level 1.
        self.connection.execute("UPDATE levels SET level = 1 WHERE level < 1")
        self._seed_achievements()
        self.connection.commit()

    def _seed_achievements(self) -> None:
        achievements = (
            (
                "first_steps",
                "First Steps",
                "أرسل أول رسالة لك في السيرفر.",
                "🏆",
                "messages",
                1,
                "Common",
                None,
            ),
            (
                "talkative",
                "Talkative",
                "أرسل 100 رسالة مؤهلة للحصول على XP.",
                "💬",
                "messages",
                100,
                "Common",
                None,
            ),
            (
                "social",
                "Social",
                "أرسل 1,000 رسالة مؤهلة للحصول على XP.",
                "💬",
                "messages",
                1000,
                "Uncommon",
                None,
            ),
            (
                "dedicated",
                "Dedicated",
                "وصل إلى المستوى 10.",
                "🔥",
                "level",
                10,
                "Rare",
                None,
            ),
            (
                "veteran",
                "Veteran",
                "وصل إلى المستوى 25.",
                "🔥",
                "level",
                25,
                "Epic",
                None,
            ),
            (
                "legend",
                "Legend",
                "وصل إلى المستوى 50.",
                "👑",
                "level",
                50,
                "Legendary",
                None,
            ),
            (
                "night_owl",
                "Night Owl",
                "تفاعل في وقت متأخر من الليل لمدة 7 أيام.",
                "🌙",
                "late_night_days",
                7,
                "Rare",
                None,
            ),
        )
        self.connection.executemany(
            """
            INSERT OR IGNORE INTO achievements
                (id, name, description, emoji, requirement_type, requirement_value, rarity, reward)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            achievements,
        )

    def _ensure_guild(self, guild_id: int) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
        )
        self.connection.commit()

    def get_settings(self, guild_id: int) -> sqlite3.Row:
        self._ensure_guild(guild_id)
        return self.connection.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        ).fetchone()

    def set_setting(self, guild_id: int, key: str, value: int | None) -> None:
        allowed = {
            "welcome_channel_id",
            "logs_channel_id",
            "ticket_category_id",
            "autorole_id",
            "suggestions_channel_id",
        }
        if key not in allowed:
            raise ValueError(f"Unknown guild setting: {key}")
        self._ensure_guild(guild_id)
        self.connection.execute(
            f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?",
            (value, guild_id),
        )
        self.connection.commit()

    def add_warning(
        self, guild_id: int, user_id: int, moderator_id: int, reason: str
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                moderator_id,
                reason,
                datetime.now(UTC).isoformat(),
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def list_warnings(self, guild_id: int, user_id: int) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT * FROM warnings
                WHERE guild_id = ? AND user_id = ?
                ORDER BY id DESC
                """,
                (guild_id, user_id),
            )
        )

    def clear_warnings(self, guild_id: int, user_id: int) -> int:
        cursor = self.connection.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        self.connection.commit()
        return cursor.rowcount

    def warning_count(self, guild_id: int) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM warnings WHERE guild_id = ?", (guild_id,)
            ).fetchone()[0]
        )

    def pending_suggestion_count(self, guild_id: int) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM suggestions WHERE guild_id = ? AND status = 'pending'",
                (guild_id,),
            ).fetchone()[0]
        )

    def economy_user_count(self, guild_id: int) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM economy WHERE guild_id = ?", (guild_id,)
            ).fetchone()[0]
        )

    def level_user_count(self, guild_id: int) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM levels WHERE guild_id = ?", (guild_id,)
            ).fetchone()[0]
        )

    def add_suggestion(
        self, guild_id: int, user_id: int, content: str, message_id: int | None = None
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO suggestions (guild_id, user_id, content, message_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                content,
                message_id,
                datetime.now(UTC).isoformat(),
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def set_suggestion_message(self, suggestion_id: int, message_id: int) -> None:
        self.connection.execute(
            "UPDATE suggestions SET message_id = ? WHERE id = ?",
            (message_id, suggestion_id),
        )
        self.connection.commit()

    def update_suggestion_status(self, suggestion_id: int, status: str) -> None:
        self.connection.execute(
            "UPDATE suggestions SET status = ? WHERE id = ?",
            (status, suggestion_id),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def get_economy(self, guild_id: int, user_id: int) -> sqlite3.Row:
        self.connection.execute(
            "INSERT OR IGNORE INTO economy (guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id),
        )
        self.connection.commit()
        return self.connection.execute(
            "SELECT * FROM economy WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()

    def change_balance(self, guild_id: int, user_id: int, amount: int) -> int:
        self.get_economy(guild_id, user_id)
        self.connection.execute(
            "UPDATE economy SET balance = balance + ? WHERE guild_id = ? AND user_id = ?",
            (amount, guild_id, user_id),
        )
        self.connection.commit()
        return int(self.get_economy(guild_id, user_id)["balance"])

    def set_economy_date(self, guild_id: int, user_id: int, column: str, value: str) -> None:
        if column not in {"last_daily", "last_work"}:
            raise ValueError("Invalid economy date column")
        self.get_economy(guild_id, user_id)
        self.connection.execute(
            f"UPDATE economy SET {column} = ? WHERE guild_id = ? AND user_id = ?",
            (value, guild_id, user_id),
        )
        self.connection.commit()

    def economy_leaderboard(self, guild_id: int, limit: int = 10) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT ?",
                (guild_id, limit),
            )
        )

    def get_level(
        self, guild_id: int, user_id: int, joined_at: str | None = None
    ) -> sqlite3.Row:
        self.connection.execute(
            "INSERT OR IGNORE INTO levels (guild_id, user_id, joined_at) VALUES (?, ?, ?)",
            (guild_id, user_id, joined_at),
        )
        if joined_at:
            self.connection.execute(
                """
                UPDATE levels SET joined_at = COALESCE(joined_at, ?)
                WHERE guild_id = ? AND user_id = ?
                """,
                (joined_at, guild_id, user_id),
            )
        self.connection.commit()
        return self.connection.execute(
            "SELECT * FROM levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()

    def add_xp(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
        message_count: int = 1,
        late_night_date: str | None = None,
        joined_at: str | None = None,
    ) -> sqlite3.Row:
        current = self.get_level(guild_id, user_id)
        xp = int(current["xp"]) + amount
        level = int(current["level"])
        self.connection.execute(
            """
            UPDATE levels
            SET xp = xp + ?, message_count = message_count + ?,
                joined_at = COALESCE(joined_at, ?)
            WHERE guild_id = ? AND user_id = ?
            """,
            (amount, message_count, joined_at, guild_id, user_id),
        )
        if late_night_date:
            self.connection.execute(
                """
                UPDATE levels
                SET late_night_days = late_night_days + 1,
                    last_late_night_date = ?
                WHERE guild_id = ? AND user_id = ?
                  AND (last_late_night_date IS NULL OR last_late_night_date != ?)
                """,
                (late_night_date, guild_id, user_id, late_night_date),
            )
        while xp >= self.xp_for_level(level + 1):
            level += 1
        self.connection.execute(
            "UPDATE levels SET level = ? WHERE guild_id = ? AND user_id = ?",
            (level, guild_id, user_id),
        )
        self.connection.commit()
        return self.get_level(guild_id, user_id)

    @staticmethod
    def xp_for_level(level: int) -> int:
        from .config import LEVEL_BASE_XP, LEVEL_GROWTH_XP

        safe_level = max(level - 1, 0)
        return LEVEL_BASE_XP * safe_level + (
            LEVEL_GROWTH_XP * safe_level * max(safe_level - 1, 0) // 2
        )

    @classmethod
    def level_for_xp(cls, xp: int) -> int:
        level = 1
        while xp >= cls.xp_for_level(level + 1):
            level += 1
        return level

    def set_level_values(
        self, guild_id: int, user_id: int, xp: int, level: int
    ) -> sqlite3.Row:
        self.get_level(guild_id, user_id)
        self.connection.execute(
            "UPDATE levels SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?",
            (max(xp, 0), max(level, 1), guild_id, user_id),
        )
        self.connection.commit()
        return self.get_level(guild_id, user_id)

    def level_leaderboard(
        self,
        guild_id: int,
        limit: int = 10,
        offset: int = 0,
        sort_mode: str = "xp",
    ) -> list[sqlite3.Row]:
        if sort_mode not in {"xp", "level"}:
            raise ValueError("Invalid level leaderboard sort mode")
        order_by = "xp DESC, level DESC" if sort_mode == "xp" else "level DESC, xp DESC"
        return list(
            self.connection.execute(
                f"""
                SELECT * FROM levels
                WHERE guild_id = ?
                ORDER BY {order_by}, user_id ASC
                LIMIT ? OFFSET ?
                """,
                (guild_id, limit, offset),
            )
        )

    def level_rank(self, guild_id: int, user_id: int) -> int:
        row = self.get_level(guild_id, user_id)
        return int(
            self.connection.execute(
                """
                SELECT COUNT(*) + 1 FROM levels
                WHERE guild_id = ? AND (xp > ? OR (xp = ? AND user_id < ?))
                """,
                (guild_id, row["xp"], row["xp"], user_id),
            ).fetchone()[0]
        )

    def count_levels(self, guild_id: int) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM levels WHERE guild_id = ?", (guild_id,)
            ).fetchone()[0]
        )

    def list_achievements(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM achievements ORDER BY requirement_value, id"
            )
        )

    def user_achievements(
        self, guild_id: int, user_id: int
    ) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT a.*, ua.unlocked_at
                FROM achievements a
                JOIN user_achievements ua ON ua.achievement_id = a.id
                WHERE ua.guild_id = ? AND ua.user_id = ?
                ORDER BY ua.unlocked_at ASC
                """,
                (guild_id, user_id),
            )
        )

    def unlock_achievement(
        self, guild_id: int, user_id: int, achievement_id: str
    ) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO user_achievements
                (guild_id, user_id, achievement_id, unlocked_at)
            VALUES (?, ?, ?, ?)
            """,
            (guild_id, user_id, achievement_id, datetime.now(UTC).isoformat()),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def unlocked_achievement_ids(self, guild_id: int, user_id: int) -> set[str]:
        return {
            str(row["achievement_id"])
            for row in self.connection.execute(
                """
                SELECT achievement_id FROM user_achievements
                WHERE guild_id = ? AND user_id = ?
                """,
                (guild_id, user_id),
            )
        }

    def achievement_count(self, guild_id: int, user_id: int) -> int:
        return int(
            self.connection.execute(
                """
                SELECT COUNT(*) FROM user_achievements
                WHERE guild_id = ? AND user_id = ?
                """,
                (guild_id, user_id),
            ).fetchone()[0]
        )

    def create_giveaway(
        self, guild_id: int, channel_id: int, prize: str, ends_at: str
    ) -> int:
        cursor = self.connection.execute(
            "INSERT INTO giveaways (guild_id, channel_id, prize, ends_at) VALUES (?, ?, ?, ?)",
            (guild_id, channel_id, prize, ends_at),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def set_giveaway_message(self, giveaway_id: int, message_id: int) -> None:
        self.connection.execute(
            "UPDATE giveaways SET message_id = ? WHERE id = ?", (message_id, giveaway_id)
        )
        self.connection.commit()

    def get_giveaway(self, giveaway_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM giveaways WHERE id = ?", (giveaway_id,)
        ).fetchone()

    def active_giveaways(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM giveaways WHERE ended = 0"))

    def end_giveaway(self, giveaway_id: int) -> None:
        self.connection.execute(
            "UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_id,)
        )
        self.connection.commit()

    def add_giveaway_entry(self, giveaway_id: int, user_id: int) -> bool:
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
            (giveaway_id, user_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def giveaway_entries(self, giveaway_id: int) -> list[int]:
        return [
            int(row["user_id"])
            for row in self.connection.execute(
                "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?",
                (giveaway_id,),
            )
        ]

    def add_reaction_role(
        self, guild_id: int, message_id: int, role_id: int, emoji: str
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO reaction_roles (guild_id, message_id, role_id, emoji)
            VALUES (?, ?, ?, ?)
            """,
            (guild_id, message_id, role_id, emoji),
        )
        self.connection.commit()

    def reaction_role(self, message_id: int, emoji: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM reaction_roles WHERE message_id = ? AND emoji = ?",
            (message_id, emoji),
        ).fetchone()

    def custom_command(self, guild_id: int, name: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM custom_commands WHERE guild_id = ? AND name = ?",
            (guild_id, name.lower()),
        ).fetchone()

    def set_custom_command(self, guild_id: int, name: str, response: str) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO custom_commands (guild_id, name, response) VALUES (?, ?, ?)",
            (guild_id, name.lower(), response),
        )
        self.connection.commit()

    def delete_custom_command(self, guild_id: int, name: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM custom_commands WHERE guild_id = ? AND name = ?",
            (guild_id, name.lower()),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_custom_commands(self, guild_id: int) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM custom_commands WHERE guild_id = ? ORDER BY name",
                (guild_id,),
            )
        )
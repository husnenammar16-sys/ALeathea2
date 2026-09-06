from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from discord_bot.bot import AlythiaBot
from discord_bot.cogs.levels import Levels
from discord_bot.database import Database


class LevelsDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(str(Path(self.temp_dir.name) / "levels.sqlite3"))

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def test_progression_and_achievements_are_scoped_to_guild_and_user(self) -> None:
        guild_one = 101
        guild_two = 202
        user_one = 11
        user_two = 22

        first = self.database.add_xp(guild_one, user_one, 250)
        self.database.add_xp(guild_one, user_two, 10)
        self.database.add_xp(guild_two, user_one, 10)
        self.assertEqual((first["xp"], first["level"]), (250, 3))

        self.assertTrue(self.database.unlock_achievement(guild_one, user_one, "first_steps"))
        self.assertEqual(self.database.unlocked_achievement_ids(guild_one, user_one), {"first_steps"})
        self.assertEqual(self.database.unlocked_achievement_ids(guild_one, user_two), set())
        self.assertEqual(self.database.unlocked_achievement_ids(guild_two, user_one), set())
        self.assertEqual(self.database.get_level(guild_one, user_one)["level"], 3)
        self.assertEqual(self.database.get_level(guild_one, user_two)["xp"], 10)
        self.assertEqual(self.database.get_level(guild_two, user_one)["xp"], 10)

    def test_achievement_unlock_is_idempotent(self) -> None:
        self.assertTrue(self.database.unlock_achievement(1, 2, "first_steps"))
        self.assertFalse(self.database.unlock_achievement(1, 2, "first_steps"))
        self.assertEqual(self.database.achievement_count(1, 2), 1)

        levels = Levels(None, self.database)
        row = self.database.add_xp(3, 4, 10)
        self.assertEqual(
            [achievement["id"] for achievement in levels._new_achievements(3, 4, row)],
            ["first_steps"],
        )
        self.assertEqual(levels._new_achievements(3, 4, row), [])

    def test_xp_survives_closing_and_reopening_sqlite(self) -> None:
        path = Path(self.temp_dir.name) / "restart.sqlite3"
        self.database.close()
        self.database = Database(str(path))
        row = self.database.add_xp(7, 8, 250, message_count=3)
        self.database.unlock_achievement(7, 8, "first_steps")
        self.database.close()

        self.database = Database(str(path))
        persisted = self.database.get_level(7, 8)
        self.assertEqual(
            (persisted["xp"], persisted["level"], persisted["message_count"]),
            (row["xp"], row["level"], 3),
        )
        self.assertEqual(self.database.unlocked_achievement_ids(7, 8), {"first_steps"})

    def test_xp_state_is_scoped_per_guild_and_user(self) -> None:
        levels = Levels(None, self.database)
        messages = [
            self._message(1, 9, "hello from guild one"),
            self._message(2, 9, "hello from guild two"),
            self._message(1, 10, "hello from another user"),
        ]
        with patch(
            "discord_bot.cogs.levels.time",
            SimpleNamespace(monotonic=Mock(side_effect=[100, 100, 100])),
        ), patch(
            "discord_bot.cogs.levels.random.randint", return_value=10
        ):
            asyncio.run(self._send_messages(levels, messages))

        self.assertEqual(self.database.get_level(1, 9)["xp"], 10)
        self.assertEqual(self.database.get_level(2, 9)["xp"], 10)
        self.assertEqual(self.database.get_level(1, 10)["xp"], 10)

    def test_xp_requires_length_and_respects_cooldown_repeat_and_spam_limits(self) -> None:
        levels = Levels(None, self.database)
        short = self._message(1, 1, " a \n b ")
        with patch(
            "discord_bot.cogs.levels.time",
            SimpleNamespace(monotonic=Mock(return_value=100)),
        ), patch(
            "discord_bot.cogs.levels.random.randint", return_value=10
        ):
            asyncio.run(self._send_messages(levels, [short]))
        self.assertEqual(self.database.count_levels(1), 0)

        cooldown_messages = [
            self._message(1, 1, "first eligible message"),
            self._message(1, 1, "second eligible message"),
            self._message(1, 1, "third eligible message"),
        ]
        with patch(
            "discord_bot.cogs.levels.time",
            SimpleNamespace(monotonic=Mock(side_effect=[100, 101, 161])),
        ), patch("discord_bot.cogs.levels.random.randint", return_value=10):
            asyncio.run(self._send_messages(levels, cooldown_messages))
        self.assertEqual(self.database.get_level(1, 1)["message_count"], 2)

        repeat_levels = Levels(None, self.database)
        repeated = [
            self._message(1, 2, "same eligible message"),
            self._message(1, 2, " SAME   eligible\nmessage "),
        ]
        with patch(
            "discord_bot.cogs.levels.time",
            SimpleNamespace(monotonic=Mock(side_effect=[200, 261])),
        ), patch(
            "discord_bot.cogs.levels.random.randint", return_value=10
        ):
            asyncio.run(self._send_messages(repeat_levels, repeated))
        self.assertEqual(self.database.get_level(1, 2)["message_count"], 1)

        spam_levels = Levels(None, self.database)
        spam_messages = [
            self._message(1, 3, f"unique spam message {index}") for index in range(7)
        ]
        with patch(
            "discord_bot.cogs.levels.time",
            SimpleNamespace(
                monotonic=Mock(side_effect=[300, 301, 302, 303, 304, 305, 361])
            ),
        ), patch("discord_bot.cogs.levels.random.randint", return_value=10):
            asyncio.run(self._send_messages(spam_levels, spam_messages))
        self.assertEqual(self.database.get_level(1, 3)["message_count"], 2)

    async def _send_messages(
        self, levels: Levels, messages: list[SimpleNamespace]
    ) -> None:
        for message in messages:
            await levels.on_message(message)

    @staticmethod
    def _message(guild_id: int, user_id: int, content: str) -> SimpleNamespace:
        return SimpleNamespace(
            guild=SimpleNamespace(id=guild_id),
            author=SimpleNamespace(
                id=user_id,
                bot=False,
                joined_at=None,
                mention=f"<@{user_id}>",
            ),
            content=content,
            channel=SimpleNamespace(send=AsyncMock()),
        )


class CommandRegistrationTests(unittest.TestCase):
    def test_level_commands_register_without_name_collisions(self) -> None:
        async def check_commands() -> list[str]:
            database = Database(":memory:")
            bot = AlythiaBot(database)
            try:
                await bot.setup_hook()
                return [command.name for command in bot.tree.get_commands()]
            finally:
                await bot.close()
                database.close()

        names = asyncio.run(check_commands())
        self.assertEqual(len(names), len(set(names)))
        for command_name in ("profile", "rank", "achievements", "leaderboard"):
            self.assertIn(command_name, names)


if __name__ == "__main__":
    unittest.main()
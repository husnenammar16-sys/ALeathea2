---
name: Discord guild command sync
description: Guild-specific slash command sync requires copying global commands into each guild first.
---

Before calling `tree.sync(guild=...)`, copy the global command tree into that guild with `tree.copy_global_to(guild=...)`; otherwise the sync succeeds but publishes zero commands. If using guild-only commands for fast updates, clear and sync the global tree afterward so users do not see duplicates.

**Why:** A global tree and a guild-scoped tree are separate command collections in discord.py, so a guild sync without the copy step silently returns an empty command set.

**How to apply:** Use guild sync after ready for immediate updates during development, while keeping global sync if the bot will later serve additional servers.
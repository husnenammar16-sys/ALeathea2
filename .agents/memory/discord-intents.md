---
name: Discord privileged intents
description: Discord community bots need privileged Gateway Intents enabled on the exact application that issued the bot token.
---

Enable Server Members Intent and Message Content Intent in the same Discord Developer Portal application that generated the stored bot token. If Discord still returns PrivilegedIntentsRequired, the token usually belongs to a different application; reset that application's token and update the secret.

**Why:** Discord validates privileged intents against the bot application associated with the token, not against the server invitation or a separate Discord account connection.

**How to apply:** When a bot fails at Gateway login with PrivilegedIntentsRequired, verify the app/token pairing first, then restart the bot.
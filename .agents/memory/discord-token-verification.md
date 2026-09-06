---
name: Discord token verification
description: REST token preflight can fail even when the Discord gateway connection is healthy.
---

The bot's REST preflight request to `users/@me` may return HTTP 403 while the same token successfully connects through the Discord Gateway and reaches `on_ready`.

**Why:** Gateway connectivity is the reliable signal that the token is usable for the running bot; a REST preflight failure should not be treated as proof that the token is invalid.

**How to apply:** Keep the preflight non-fatal and verify successful startup through the gateway and guild command synchronization logs.
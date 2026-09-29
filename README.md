# VJ Join Request Acceptor Bot

Advanced Telegram join-request manager based on Pyrofork + MongoDB.

## Features
- Add-to-Channel and Add-to-Group start buttons
- Help, Support, Update Channel and Support Group buttons
- Telegram account login/logout with session storage
- Accept pending requests from both groups and channels
- Per-user daily success/dead/error statistics
- Final DM report after `/accept`
- `/mystats` personal report
- Optional automatic new-request approval via `NEW_REQ_MODE=true`
- Admin-only advanced panel via `/admin`
- Global daily statistics
- 7-day report
- Top users
- Recent acceptance activity
- Recent users
- Active session count
- MongoDB health check
- Bot uptime and bot info
- Broadcast with success/blocked/deleted/failed/completed stats
- Broadcast history
- Admin-only controls and callbacks
- MongoDB-backed data

## Environment variables
`API_ID`, `API_HASH`, `BOT_TOKEN`, `DB_URI`, `DB_NAME`, `ADMINS`, `LOG_CHANNEL`, `NEW_REQ_MODE`

`ADMINS` can contain comma-separated Telegram IDs.

## Render start command
```text
gunicorn app:app & python3 bot.py
```

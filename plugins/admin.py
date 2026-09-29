import asyncio
import datetime
import time

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from config import ADMINS, NEW_REQ_MODE
from plugins.database import db

START_TIME = time.monotonic()
ADMIN_IDS = set(ADMINS if isinstance(ADMINS, (list, tuple, set)) else [ADMINS])


def panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Overview", callback_data="adm:overview"), InlineKeyboardButton("📈 Today", callback_data="adm:today")],
        [InlineKeyboardButton("👥 Users", callback_data="adm:users"), InlineKeyboardButton("🔐 Sessions", callback_data="adm:sessions")],
        [InlineKeyboardButton("🏆 Top Users", callback_data="adm:top"), InlineKeyboardButton("📝 Recent Accepts", callback_data="adm:recent")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm:broadcast"), InlineKeyboardButton("📜 Broadcast History", callback_data="adm:broadcasts")],
        [InlineKeyboardButton("⚡ Auto Mode", callback_data="adm:automode"), InlineKeyboardButton("🗄 DB Health", callback_data="adm:db")],
        [InlineKeyboardButton("⏱ Uptime", callback_data="adm:uptime"), InlineKeyboardButton("ℹ️ Bot Info", callback_data="adm:info")],
        [InlineKeyboardButton("📅 7 Day Report", callback_data="adm:7day"), InlineKeyboardButton("📆 Yesterday", callback_data="adm:yesterday")],
        [InlineKeyboardButton("🗓 30 Day Report", callback_data="adm:30day"), InlineKeyboardButton("🔥 Active Users", callback_data="adm:active")],
        [InlineKeyboardButton("🧩 DB Collections", callback_data="adm:collections"), InlineKeyboardButton("⚙️ Config Status", callback_data="adm:config")],
        [InlineKeyboardButton("📚 Admin Help", callback_data="adm:help"), InlineKeyboardButton("🔄 Refresh", callback_data="adm:overview")],
        [InlineKeyboardButton("❌ Close", callback_data="adm:close")],
    ])


def is_admin(user_id):
    return int(user_id) in ADMIN_IDS


def fmt_uptime():
    seconds = int(time.monotonic() - START_TIME)
    d, seconds = divmod(seconds, 86400)
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    return f"{d}d {h}h {m}m {s}s"


@Client.on_message(filters.command("admin") & filters.private & filters.user(ADMINS))
async def admin_command(client, message):
    await message.reply_text("<b>🛠 Advanced Admin Panel</b>\n\nChoose an option:", reply_markup=panel())


@Client.on_message(filters.command("stats") & filters.private & filters.user(ADMINS))
async def admin_stats(client, message):
    s = await db.get_global_stats()
    await message.reply_text(
        "<b>📊 Global Today Stats</b>\n\n"
        f"👥 Users: <code>{await db.total_users_count()}</code>\n"
        f"🔐 Sessions: <code>{await db.active_sessions_count()}</code>\n"
        f"📨 Requests: <code>{s.get('total', 0)}</code>\n"
        f"✅ Success: <code>{s.get('success', 0)}</code>\n"
        f"💀 Dead: <code>{s.get('dead', 0)}</code>\n"
        f"⚠️ Error: <code>{s.get('error', 0)}</code>\n"
        f"⚡ Auto mode: <code>{'ON' if NEW_REQ_MODE else 'OFF'}</code>\n"
        f"⏱ Uptime: <code>{fmt_uptime()}</code>",
        reply_markup=panel(),
    )


@Client.on_message(filters.command("ban") & filters.private & filters.user(ADMINS))
async def ban_user(client, message):
    if len(message.command) < 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/ban USER_ID</code>")
    uid = int(message.command[1])
    await db.set_ban(uid, "Admin ban")
    await message.reply_text(f"<b>🚫 User banned:</b> <code>{uid}</code>")


@Client.on_message(filters.command("unban") & filters.private & filters.user(ADMINS))
async def unban_user(client, message):
    if len(message.command) < 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/unban USER_ID</code>")
    uid = int(message.command[1])
    await db.remove_ban(uid)
    await message.reply_text(f"<b>✅ User unbanned:</b> <code>{uid}</code>")


async def render_admin(client, query, action):
    if action in ("overview", "today"):
        s = await db.get_global_stats()
        text = (
            "<b>📊 Admin Overview</b>\n\n"
            f"👥 Total Users: <code>{await db.total_users_count()}</code>\n"
            f"🔐 Logged-in Accounts: <code>{await db.active_sessions_count()}</code>\n"
            f"📨 Today's Requests: <code>{s.get('total', 0)}</code>\n"
            f"✅ Success: <code>{s.get('success', 0)}</code>\n"
            f"💀 Dead: <code>{s.get('dead', 0)}</code>\n"
            f"⚠️ Errors: <code>{s.get('error', 0)}</code>\n"
            f"⚡ Auto Approval: <code>{'ON' if NEW_REQ_MODE else 'OFF'}</code>\n"
            f"⏱ Uptime: <code>{fmt_uptime()}</code>"
        )
    elif action == "users":
        users = await db.get_recent_users(10)
        lines = [f"<b>👥 Recent Users ({len(users)})</b>"]
        for u in users:
            lines.append(f"• <code>{u.get('id')}</code> — {u.get('name','Unknown')}")
        text = "\n".join(lines)
    elif action == "sessions":
        text = f"<b>🔐 Active Sessions</b>\n\nConnected Telegram accounts: <code>{await db.active_sessions_count()}</code>"
    elif action == "top":
        rows = await db.get_top_users(limit=10)
        lines = ["<b>🏆 Top Users Today</b>"]
        for i, row in enumerate(rows, 1):
            lines.append(f"{i}. <code>{row.get('user_id')}</code> — ✅ {row.get('success',0)} | 💀 {row.get('dead',0)} | ⚠️ {row.get('error',0)}")
        text = "\n".join(lines)
    elif action == "recent":
        rows = await db.get_recent_accepts(12)
        lines = ["<b>📝 Recent Accept Activity</b>"]
        for row in rows:
            title = row.get("chat_title") or "Unknown"
            lines.append(f"• <code>{row.get('user_id')}</code> | {row.get('status')} | {title} | +{row.get('amount',1)}")
        text = "\n".join(lines)
    elif action == "broadcasts":
        rows = await db.get_broadcasts(10)
        lines = ["<b>📜 Broadcast History</b>"]
        for row in rows:
            lines.append(f"• {row.get('started_at')} | ✅ {row.get('success',0)} | 🚫 {row.get('blocked',0)} | ⚠️ {row.get('failed',0)}")
        text = "\n".join(lines)
    elif action == "automode":
        text = "<b>⚡ Auto Join Request Mode</b>\n\nCurrent: <code>{}</code>\n\nThis value comes from NEW_REQ_MODE at startup.".format("ON" if NEW_REQ_MODE else "OFF")
    elif action == "db":
        try:
            await db.db_ping()
            text = "<b>🗄 Database Health</b>\n\n✅ MongoDB ping successful.\n✅ Database connection is responding."
        except Exception as e:
            text = f"<b>🗄 Database Health</b>\n\n❌ MongoDB error:\n<code>{str(e)[:700]}</code>"
    elif action == "uptime":
        text = f"<b>⏱ Bot Uptime</b>\n\n<code>{fmt_uptime()}</code>"
    elif action == "info":
        text = "<b>ℹ️ Bot Info</b>\n\nJoin Request Acceptor\nPyrofork + MongoDB\nAdmin tools + broadcast + per-user statistics enabled."
    elif action == "7day":
        today = datetime.datetime.now(datetime.timezone.utc).date()
        total = success = dead = error = 0
        for i in range(7):
            day = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            s = await db.get_global_stats(day)
            total += s.get("total", 0)
            success += s.get("success", 0)
            dead += s.get("dead", 0)
            error += s.get("error", 0)
        text = f"<b>📅 Last 7 Days</b>\n\n📨 Total: <code>{total}</code>\n✅ Success: <code>{success}</code>\n💀 Dead: <code>{dead}</code>\n⚠️ Error: <code>{error}</code>"
    elif action == "broadcast":
        text = "<b>📢 Broadcast</b>\n\nReply to any message with <code>/broadcast</code> in this private chat.\nOnly configured admins can use it.\n\nThe result includes total, completed, success, blocked, deleted and failed counts."
    elif action == "yesterday":
        day = (datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        s = await db.get_global_stats(day)
        text = f"<b>📆 Yesterday ({day})</b>\n\n📨 Total: <code>{s.get('total',0)}</code>\n✅ Success: <code>{s.get('success',0)}</code>\n💀 Dead: <code>{s.get('dead',0)}</code>\n⚠️ Error: <code>{s.get('error',0)}</code>"
    elif action == "30day":
        today = datetime.datetime.now(datetime.timezone.utc).date()
        total = success = dead = error = 0
        for i in range(30):
            day = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            s = await db.get_global_stats(day)
            total += s.get("total",0); success += s.get("success",0); dead += s.get("dead",0); error += s.get("error",0)
        text = f"<b>🗓 Last 30 Days</b>\n\n📨 Total: <code>{total}</code>\n✅ Success: <code>{success}</code>\n💀 Dead: <code>{dead}</code>\n⚠️ Error: <code>{error}</code>"
    elif action == "active":
        now = datetime.datetime.now(datetime.timezone.utc)
        since = now - datetime.timedelta(days=1)
        count = await db.col.count_documents({"last_seen": {"$gte": since}})
        text = f"<b>🔥 Active Users</b>\n\nUsers active in the last 24 hours: <code>{count}</code>"
    elif action == "collections":
        names = await db.db.list_collection_names()
        text = "<b>🧩 MongoDB Collections</b>\n\n" + "\n".join(f"• <code>{n}</code>" for n in names)
    elif action == "config":
        text = ("<b>⚙️ Config Status</b>\n\n"
                f"👑 Admin IDs: <code>{len(ADMIN_IDS)}</code>\n"
                f"⚡ NEW_REQ_MODE: <code>{'ON' if NEW_REQ_MODE else 'OFF'}</code>\n"
                "🔐 DB URI: <code>configured</code>\n"
                "🤖 Bot Token: <code>configured</code>")
    elif action == "help":
        text = ("<b>📚 Admin Help</b>\n\n"
                "• /admin — open panel\n"
                "• /stats — global daily stats\n"
                "• /broadcast — reply to a message to broadcast it\n"
                "• /ban USER_ID — ban a bot user\n"
                "• /unban USER_ID — remove a bot-user ban\n\n"
                "All panel buttons are restricted to configured ADMINS.")
    else:
        text = "<b>Advanced Admin Panel</b>"
    return text


@Client.on_callback_query(filters.regex(r"^adm:"))
async def admin_callback(client, query):
    if not is_admin(query.from_user.id):
        await query.answer("Admin only.", show_alert=True)
        return
    action = query.data.split(":", 1)[1]
    if action == "close":
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass
        return
    await query.answer()
    text = await render_admin(client, query, action)
    await query.message.edit_text(text, reply_markup=panel())

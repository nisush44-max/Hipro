import asyncio
import datetime
import logging
import time

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError, UserNotParticipant

from config import LOG_CHANNEL, API_ID, API_HASH, NEW_REQ_MODE, ADMINS
from plugins.database import db

LOG_TEXT = """<b>#NewUser

ID - <code>{}</code>

Nᴀᴍᴇ - {}</b>"""

START_IMAGE = "https://te.legra.ph/file/119729ea3cdce4fefb6a1.jpg"


def start_keyboard(username):
    username = (username or "RequestApprovalBot").lstrip("@")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add To Channel", url=f"https://t.me/{username}?startchannel=true"),
            InlineKeyboardButton("➕ Add To Group", url=f"https://t.me/{username}?startgroup=true"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
            InlineKeyboardButton("🆘 Support", url="https://t.me/vj_bot_disscussion"),
        ],
        [
            InlineKeyboardButton("📢 Update Channel", url="https://t.me/VJ_Botz"),
            InlineKeyboardButton("👥 Support Group", url="https://t.me/vj_bot_disscussion"),
        ],
    ])


@Client.on_message(filters.command("start"))
async def start_message(c, m):
    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id, m.from_user.first_name)
        try:
            await c.send_message(LOG_CHANNEL, LOG_TEXT.format(m.from_user.id, m.from_user.mention))
        except Exception:
            pass
    else:
        await db.touch_user(m.from_user.id, m.from_user.first_name)

    await m.reply_photo(
        START_IMAGE,
        caption=(
            f"<b>Hello {m.from_user.mention} 👋</b>\n\n"
            "<b>I Am Join Request Acceptor Bot.</b>\n"
            "Accept pending join requests from your channel/group using your own Telegram account.\n\n"
            "<b>Commands:</b>\n"
            "• /login — Connect your Telegram account\n"
            "• /accept — Accept pending requests\n"
            "• /mystats — Today's acceptance stats\n"
            "• /logout — Remove your login session"
        ),
        reply_markup=start_keyboard(c.username),
    )


@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(client, query):
    await query.answer()
    await query.message.reply_text(
        "<b>📚 Help</b>\n\n"
        "1. Add this bot as admin to your channel/group.\n"
        "2. Send /login and connect your Telegram account.\n"
        "3. Send /accept.\n"
        "4. Forward any message from your channel/group.\n"
        "5. The bot will process pending join requests and send you a final report.\n\n"
        "Use /mystats anytime to see today's success/dead/error counts."
    )


async def approve_pending_requests(acc, chat_id, owner_id, chat_title, status_msg):
    result = {"attempted": 0, "success": 0, "dead": 0, "error": 0}
    started = time.monotonic()

    while True:
        requests = [r async for r in acc.get_chat_join_requests(chat_id, limit=100)]
        if not requests:
            break

        for req in requests:
            result["attempted"] += 1
            try:
                await acc.approve_chat_join_request(chat_id, req.user.id)
                result["success"] += 1
                await db.record_accept(owner_id, "success", chat_id, chat_title)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await acc.approve_chat_join_request(chat_id, req.user.id)
                    result["success"] += 1
                    await db.record_accept(owner_id, "success", chat_id, chat_title)
                except Exception:
                    result["error"] += 1
                    await db.record_accept(owner_id, "error", chat_id, chat_title)
            except (UserNotParticipant, RPCError):
                result["dead"] += 1
                await db.record_accept(owner_id, "dead", chat_id, chat_title)
            except Exception as exc:
                logging.warning("Join request approval failed for %s: %s", req.user.id, exc)
                result["error"] += 1
                await db.record_accept(owner_id, "error", chat_id, chat_title)

            if result["attempted"] % 20 == 0:
                elapsed = int(time.monotonic() - started)
                try:
                    await status_msg.edit(
                        "<b>⚡ Processing join requests...</b>\n\n"
                        f"📨 Attempted: <code>{result['attempted']}</code>\n"
                        f"✅ Success: <code>{result['success']}</code>\n"
                        f"💀 Dead: <code>{result['dead']}</code>\n"
                        f"⚠️ Error: <code>{result['error']}</code>\n"
                        f"⏱ Time: <code>{elapsed}s</code>"
                    )
                except Exception:
                    pass

    return result, int(time.monotonic() - started)


@Client.on_message(filters.command("accept") & filters.private)
async def accept(client, message):
    show = await message.reply_text("<b>⏳ Please wait...</b>")
    await db.touch_user(message.from_user.id, message.from_user.first_name)
    user_data = await db.get_session(message.from_user.id)
    if user_data is None:
        await show.edit("<b>❌ Please /login first to accept pending requests.</b>")
        return

    acc = Client(
        f"joinrequest_{message.from_user.id}",
        session_string=user_data,
        api_hash=API_HASH,
        api_id=API_ID,
        in_memory=True,
    )
    try:
        await acc.connect()
    except Exception:
        await show.edit("<b>❌ Your login session expired. Use /logout and then /login again.</b>")
        return

    try:
        await show.edit(
            "<b>📩 Forward a message from your channel or group.</b>\n\n"
            "Make sure the logged-in account is an admin there with permission to manage join requests."
        )
        vj = await client.listen(message.chat.id, timeout=300)
        if not vj.forward_from_chat or vj.forward_from_chat.type in [enums.ChatType.PRIVATE, enums.ChatType.BOT]:
            await show.edit("<b>❌ Message was not forwarded from a channel/group.</b>")
            return

        chat_id = vj.forward_from_chat.id
        try:
            info = await acc.get_chat(chat_id)
        except Exception:
            await show.edit("<b>❌ The logged-in account is not an admin or cannot access this channel/group.</b>")
            return

        try:
            await vj.delete()
        except Exception:
            pass

        chat_title = info.title or "Unknown Chat"
        chat_type = "Channel" if info.type == enums.ChatType.CHANNEL else "Group"
        await show.edit(
            f"<b>🚀 Starting...</b>\n\n"
            f"Chat: <b>{chat_title}</b>\n"
            f"Type: <b>{chat_type}</b>"
        )

        result, seconds = await approve_pending_requests(acc, chat_id, message.from_user.id, chat_title, show)
        stats = await db.get_user_stats(message.from_user.id)

        await show.edit(
            "<b>🎉 Join Request Processing Complete</b>\n\n"
            f"📣 <b>{chat_title}</b>\n"
            f"🗂 Type: <b>{chat_type}</b>\n\n"
            f"📨 Total: <code>{result['attempted']}</code>\n"
            f"✅ Success: <code>{result['success']}</code>\n"
            f"💀 Dead: <code>{result['dead']}</code>\n"
            f"⚠️ Error: <code>{result['error']}</code>\n"
            f"⏱ Time: <code>{seconds}s</code>\n\n"
            "<b>📊 Today Your Stats</b>\n"
            f"✅ Success: <code>{stats.get('success', 0)}</code>\n"
            f"💀 Dead: <code>{stats.get('dead', 0)}</code>\n"
            f"⚠️ Error: <code>{stats.get('error', 0)}</code>\n"
            f"📈 Total: <code>{stats.get('total', 0)}</code>"
        )
    except asyncio.TimeoutError:
        await show.edit("<b>⌛ Timed out. Send /accept again when you are ready.</b>")
    except Exception as e:
        logging.exception("accept failed")
        try:
            await show.edit(f"<b>❌ Error:</b> <code>{str(e)[:700]}</code>")
        except Exception:
            pass
    finally:
        try:
            await acc.disconnect()
        except Exception:
            pass


@Client.on_message(filters.command("mystats") & filters.private)
async def my_stats(client, message):
    s = await db.get_user_stats(message.from_user.id)
    await message.reply_text(
        "<b>📊 Your Today's Join Request Stats</b>\n\n"
        f"📅 <code>{s.get('day', db.today_key())}</code>\n"
        f"📨 Total: <code>{s.get('total', 0)}</code>\n"
        f"✅ Success: <code>{s.get('success', 0)}</code>\n"
        f"💀 Dead: <code>{s.get('dead', 0)}</code>\n"
        f"⚠️ Error: <code>{s.get('error', 0)}</code>"
    )


@Client.on_chat_join_request(filters.group | filters.channel)
async def approve_new(client, m):
    if not NEW_REQ_MODE:
        return
    try:
        await client.approve_chat_join_request(m.chat.id, m.from_user.id)
        try:
            await client.send_message(
                m.from_user.id,
                f"<b>✅ Your join request for {m.chat.title} was accepted.</b>\n\nPowered By @VJ_Botz",
            )
        except Exception:
            pass
    except Exception as e:
        logging.warning("Auto approval failed: %s", e)

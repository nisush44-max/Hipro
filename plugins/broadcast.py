from pyrogram.errors import InputUserDeactivated, FloodWait, UserIsBlocked, PeerIdInvalid
from pyrogram import Client, filters
from config import ADMINS
from plugins.database import db
import asyncio
import datetime
import time
import logging

logger = logging.getLogger(__name__)

async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        return False, "Deleted"
    except UserIsBlocked:
        await db.delete_user(int(user_id))
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        return False, "Deleted"
    except Exception:
        return False, "Error"


@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_command(bot, message):
    users = await db.get_all_users()
    b_msg = message.reply_to_message
    sts = await message.reply_text("<b>📢 Broadcast started...</b>")
    start_time = time.time()
    total_users = await db.total_users_count()
    done = success = blocked = deleted = failed = 0

    async for user in users:
        user_id = user.get("id")
        if not user_id:
            failed += 1
            continue
        ok, state = await broadcast_messages(int(user_id), b_msg)
        done += 1
        if ok:
            success += 1
        elif state == "Blocked":
            blocked += 1
        elif state == "Deleted":
            deleted += 1
        else:
            failed += 1

        if done % 20 == 0:
            await sts.edit(
                "<b>📢 Broadcast in progress...</b>\n\n"
                f"👥 Total: <code>{total_users}</code>\n"
                f"✅ Success: <code>{success}</code>\n"
                f"⏳ Completed: <code>{done}</code>\n"
                f"🚫 Blocked: <code>{blocked}</code>\n"
                f"🗑 Deleted: <code>{deleted}</code>\n"
                f"⚠️ Failed: <code>{failed}</code>"
            )

    elapsed = datetime.timedelta(seconds=int(time.time() - start_time))
    data = {
        "started_at": datetime.datetime.fromtimestamp(start_time, datetime.timezone.utc),
        "completed_at": datetime.datetime.now(datetime.timezone.utc),
        "total": total_users,
        "completed": done,
        "success": success,
        "blocked": blocked,
        "deleted": deleted,
        "failed": failed,
        "seconds": int(time.time() - start_time),
        "admin_id": message.from_user.id,
    }
    await db.save_broadcast(data)
    await sts.edit(
        "<b>✅ Broadcast Completed</b>\n\n"
        f"⏱ Time: <code>{elapsed}</code>\n"
        f"👥 Total: <code>{total_users}</code>\n"
        f"📨 Completed: <code>{done}</code>\n"
        f"✅ Success: <code>{success}</code>\n"
        f"🚫 Blocked: <code>{blocked}</code>\n"
        f"🗑 Deleted: <code>{deleted}</code>\n"
        f"⚠️ Failed: <code>{failed}</code>"
    )

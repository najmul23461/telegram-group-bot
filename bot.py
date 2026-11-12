"""
Telegram গ্রুপ চালানোর বট — ওয়েলকাম + স্প্যাম বন্ধ + গ্রুপ কেনার মেসেজ
ফ্রি হোস্টিং: Render (webhook)

সেটআপ দেখো: README.md
টোকেন কোডে লিখবে না — Render-এর Environment-এ BOT_TOKEN হিসেবে বসাবে।
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone

from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
# তোমার Telegram ইউজারনেম (@ ছাড়া) — Render-এ ADMIN_USERNAME হিসেবে বসাবে
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "YOUR_USERNAME")
# তোমার Telegram User ID (ঐচ্ছিক) — @userinfobot থেকে পাবে
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or 0)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # যেমন: https://telegram-group-bot-xxxx.onrender.com
PORT = int(os.environ.get("PORT", "10000"))

# লিংক ধরার প্যাটার্ন
LINK_RE = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/)", re.IGNORECASE)

# খারাপ শব্দের তালিকা — নিজের মতো বাড়াতে/কমাতে পারো
BAD_WORDS = [
    "fuck", "bitch", "shit", "bastard",
    "চুদ", "মাদারচোদ", "বোকাচোদা", "খানকি",
]

# গ্রুপ কিনতে চাইলে যে শব্দগুলো লিখলে বট উত্তর দেবে
BUY_WORDS = ["কিনতে", "কিনব", "কিনতে চাই", "buy", "price", "দাম", "কত টাকা"]

# ওয়ার্নিং গোনা (user_id -> সংখ্যা)
warnings: dict[int, int] = {}

WELCOME_TEXT = """👋 স্বাগতম {name}!

📌 গ্রুপের নিয়ম:
1️⃣ কোনো লিংক / অন্য গ্রুপের প্রমো দেবে না
2️⃣ গালি বা খারাপ ভাষা ব্যবহার করবে না
3️⃣ স্প্যাম করলে ৩ বার ওয়ার্নিং, তারপর মিউট

🛒 গ্রুপ কিনতে মেসেজ করুন @{admin}"""

BUY_TEXT = "🛒 গ্রুপ কিনতে মেসেজ করুন @{admin}"


async def is_admin(update: Update, user_id: int) -> bool:
    """ইউজার গ্রুপের অ্যাডমিন কি না দেখো।"""
    if ADMIN_ID and user_id == ADMIN_ID:
        return True
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def give_warning(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, reason: str):
    """ওয়ার্নিং দাও; ৩ বার হলে ১ ঘণ্টা মিউট করো।"""
    warnings[user_id] = warnings.get(user_id, 0) + 1
    count = warnings[user_id]
    name = update.effective_user.first_name or "বন্ধু"

    if count >= 3:
        try:
            await update.effective_chat.restrict_member(
                user_id,
                ChatPermissions(can_send_messages=False),
                until_date=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            warnings[user_id] = 0
            await update.effective_message.reply_text(
                f"⛔ {name}, ৩ বার ওয়ার্নিং পেয়েছো — ১ ঘণ্টার জন্য মিউট করা হলো।"
            )
        except Exception as e:
            logger.warning("mute failed: %s", e)
            await update.effective_message.reply_text(
                f"⚠️ {name}, ৩ বার ওয়ার্নিং! বটকে অ্যাডমিন বানাও, নাহলে মিউট করতে পারবে না।"
            )
    else:
        await update.effective_message.reply_text(
            f"⚠️ {name}, {reason} — ওয়ার্নিং {count}/3"
        )


# ---------- কমান্ড ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 আমি গ্রুপ ম্যানেজার বট।\n\n"
        "আমাকে গ্রুপে অ্যাডমিন বানালে আমি:\n"
        "✅ নতুন মেম্বারকে স্বাগতম জানাবো\n"
        "🚫 লিংক/স্প্যাম মেসেজ মুছে দেবো\n"
        "⚠️ ৩ বার ওয়ার্নিং দিলে মিউট করবো\n\n"
        f"🛒 গ্রুপ কিনতে মেসেজ করুন @{ADMIN_USERNAME}\n\n"
        "কমান্ড: /rules — নিয়ম | /buy — গ্রুপ কেনার তথ্য"
    )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 গ্রুপের নিয়ম:\n"
        "1️⃣ কোনো লিংক / অন্য গ্রুপের প্রমো দেবে না\n"
        "2️⃣ গালি বা খারাপ ভাষা ব্যবহার করবে না\n"
        "3️⃣ স্প্যাম করলে ৩ বার ওয়ার্নিং, তারপর ১ ঘণ্টা মিউট\n\n"
        f"🛒 গ্রুপ কিনতে মেসেজ করুন @{ADMIN_USERNAME}"
    )


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(BUY_TEXT.format(admin=ADMIN_USERNAME))


async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যাডমিন রিপ্লাই দিয়ে /warn লিখলে ওই ইউজারকে ওয়ার্নিং দেবে।"""
    if not update.message.reply_to_message:
        await update.message.reply_text("কাউকে ওয়ার্নিং দিতে তার মেসেজে রিপ্লাই দিয়ে /warn লেখো।")
        return
    if not await is_admin(update, update.effective_user.id):
        await update.message.reply_text("শুধু অ্যাডমিন /warn ব্যবহার করতে পারবে।")
        return
    target = update.message.reply_to_message.from_user
    await give_warning(update, context, target.id, "অ্যাডমিন ওয়ার্নিং দিয়েছে")


# ---------- গ্রুপ মেসেজ ----------

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নতুন মেম্বার জয়েন করলে স্বাগতম মেসেজ।"""
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name or "বন্ধু"
        await update.message.reply_text(
            WELCOME_TEXT.format(name=name, admin=ADMIN_USERNAME)
        )


async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """গ্রুপের প্রতিটা মেসেজ দেখে স্প্যাম/গালি/কেনার কথা ধরো।"""
    msg = update.message
    if not msg or not msg.text:
        return
    if msg.chat.type not in ("group", "supergroup"):
        return

    user = msg.from_user
    text = msg.text

    # অ্যাডমিনদের মেসেজে হাত দেবে না
    if await is_admin(update, user.id):
        return

    # ১. গ্রুপ কিনতে চাইলে উত্তর দাও
    low = text.lower()
    if any(w in text for w in BUY_WORDS) or any(w in low for w in ["buy", "price"]):
        await msg.reply_text(BUY_TEXT.format(admin=ADMIN_USERNAME))
        return

    # ২. লিংক থাকলে মুছে ওয়ার্নিং দাও
    if LINK_RE.search(text):
        try:
            await msg.delete()
        except Exception as e:
            logger.warning("delete failed: %s", e)
            return
        await give_warning(update, context, user.id, "গ্রুপে লিংক দেওয়া নিষেধ")
        return

    # ৩. খারাপ শব্দ থাকলে মুছে ওয়ার্নিং দাও
    if any(w in low for w in BAD_WORDS):
        try:
            await msg.delete()
        except Exception as e:
            logger.warning("delete failed: %s", e)
            return
        await give_warning(update, context, user.id, "খারাপ ভাষা ব্যবহার করা নিষেধ")
        return


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN দেওয়া হয়নি — Render-এর Environment-এ বসাও।")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))

    if WEBHOOK_URL:
        # Render ফ্রি প্ল্যানে webhook — ২৪ ঘণ্টা চলবে
        logger.info("Webhook mode: %s", WEBHOOK_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=WEBHOOK_URL.rstrip("/") + "/webhook",
        )
    else:
        # WEBHOOK_URL না থাকলে polling (নিজের কম্পিউটারে চালানোর জন্য)
        logger.info("Polling mode")
        app.run_polling()


if __name__ == "__main__":
    main()

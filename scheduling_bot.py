import os
import re
import pytz
import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, MessageHandler, ContextTypes, filters
)

# ENV dan tokenni o‘qish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Log sozlash
logging.basicConfig(level=logging.INFO)

# Timezone mapping
TIMEZONE_MAP = {
    'EDT': 'America/New_York',
    'EST': 'America/New_York',
    'PDT': 'America/Los_Angeles',
    'PST': 'America/Los_Angeles',
    'CDT': 'America/Chicago',
    'CST': 'America/Chicago',
}

def parse_pu_time(text: str):
    match = re.search(r"PU:\s*([A-Za-z]{3} [A-Za-z]{3} \d{1,2} \d{2}:\d{2})\s*([A-Z]+)", text)
    if not match:
        return None
    time_str, tz_abbr = match.groups()
    try:
        full_str = f"{datetime.now().year} {time_str}"
        dt = datetime.strptime(full_str, "%Y %a %b %d %H:%M")
        tz_name = TIMEZONE_MAP.get(tz_abbr)
        if not tz_name:
            return None
        return pytz.timezone(tz_name).localize(dt)
    except Exception as e:
        print("PU parsing error:", e)
        return None

def parse_offset(text: str):
    h = m = 0
    h_match = re.search(r"(\d+)\s*h", text)
    m_match = re.search(r"(\d+)\s*m", text)
    if h_match:
        h = int(h_match.group(1))
    if m_match:
        m = int(m_match.group(1))
    return timedelta(hours=h, minutes=m)

async def send_reminder(bot, chat_id, reply_to, delay_seconds):
    await asyncio.sleep(delay_seconds)
    try:
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await bot.send_message(
            chat_id=chat_id,
            text="🚨 Reminder: Load AI time is close. Please be ready.",
            reply_to_message_id=reply_to
        )
        print("✅ Reminder sent.")
    except Exception as e:
        print("❌ Reminder failed:", e)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.photo:
        return

    chat_id = msg.chat_id
    reply_to_id = msg.message_id
    caption = msg.caption or ""
    text = caption + "\n" + (msg.text or "")
    text_upper = text.upper()

    await context.bot.send_message(chat_id=chat_id, text="Noted", reply_to_message_id=reply_to_id)

    pu_time = parse_pu_time(text_upper)
    offset = parse_offset(text_upper)

    if pu_time and offset.total_seconds() > 0:
        remind_time = pu_time - offset - timedelta(minutes=10)
        remind_time_utc = remind_time.astimezone(pytz.utc)
        now_utc = datetime.now(pytz.utc)
        delay = (remind_time_utc - now_utc).total_seconds()

        print("📦 PU:", pu_time)
        print("⏱ Offset:", offset)
        print("⏰ Reminder UTC:", remind_time_utc)
        print("🕒 Now UTC:", now_utc)
        print("⌛ Delay (seconds):", delay)

        if delay > 0:
            context.application.create_task(
                send_reminder(context.bot, chat_id, reply_to_id, delay)
            )
        else:
            print("⚠️ Reminder skipped: past time")
    else:
        print("❌ PU yoki offset topilmadi")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    print("🚛 Scheduling Bot is running...")
    app.run_polling()

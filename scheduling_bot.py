import logging
import os
import re
import pytz
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

from telegram import Update, ChatAction
from telegram.ext import (
    ApplicationBuilder, MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler

# --- 1. ENV VA TOKEN O‘QISH ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- 2. LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- 3. SCHEDULER ISHLATISH ---
scheduler = BackgroundScheduler()
scheduler.start()

# --- 4. TIMEZONE MAP ---
TIMEZONE_MAP = {
    'PDT': 'America/Los_Angeles',
    'PST': 'America/Los_Angeles',
    'EDT': 'America/New_York',
    'EST': 'America/New_York',
    'CDT': 'America/Chicago',
    'CST': 'America/Chicago',
}

# --- 5. PU TIME PARSER ---
def parse_pu_time(text: str):
    match = re.search(r"PU:\s*(.+?\d{2}:\d{2})\s+([A-Z]+)", text)
    if not match:
        return None
    time_str, tz_abbr = match.groups()
    try:
        full_str = f"{datetime.now().year} {time_str}"
        dt = datetime.strptime(full_str, "%a %b %d %H:%M")
        tz_name = TIMEZONE_MAP.get(tz_abbr)
        if not tz_name:
            return None
        return pytz.timezone(tz_name).localize(dt)
    except Exception as e:
        print("Error parsing PU time:", e)
        return None

# --- 6. OFFSET PARSER ---
def parse_offset(text: str):
    h = m = 0
    h_match = re.search(r"(\d+)\s*h", text)
    m_match = re.search(r"(\d+)\s*m", text)
    if h_match:
        h = int(h_match.group(1))
    if m_match:
        m = int(m_match.group(1))
    return timedelta(hours=h, minutes=m)

# --- 7. REMINDER FUNCTION ASYNC ---
def schedule_reminder(application, chat_id, file_id, remind_time):
    async def send():
        try:
            bot = application.bot
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
            await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption="🚨 Reminder: Load pickup time is close. Please be ready."
            )
        except Exception as e:
            print("Error sending reminder:", e)

    scheduler.add_job(lambda: asyncio.run(send()), trigger="date", run_date=remind_time)

# --- 8. HANDLE MESSAGE FUNCTION ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.photo:
        return

    chat_id = message.chat_id
    caption = message.caption or ""
    text = caption + "\n" + (message.text or "")
    text_upper = text.upper()

    # ✅ Javob berish
    await message.reply_text("CHECK WITH DRIVER AND BE READY")
    await context.bot.send_message(chat_id=chat_id, text="Noted", reply_to_message_id=message.message_id)

    # ⏰ PU va OFFSET ajratish
    pu_time = parse_pu_time(text_upper)
    offset = parse_offset(text_upper)

    if pu_time and offset.total_seconds() > 0:
        remind_time = pu_time - offset - timedelta(minutes=10)
        file_id = message.photo[-1].file_id

        schedule_reminder(context.application, chat_id, file_id, remind_time)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Reminder scheduled for {remind_time.strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ PU time or offset not recognized. Format: PU: Mon May 13 20:30 EDT + offset like 2h or 30m")

# --- 9. START BOT ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    print("🚛 Scheduling Bot is running...")
    app.run_polling()

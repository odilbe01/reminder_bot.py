import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
import os
import re

# --- CONFIG ---
BOT_TOKEN = "7998824175:AAEMJBGM4z8vuzu3-OEnpPRWC3-fBiOuA1Q"
TIMEZONE_MAP = {
    'PDT': 'America/Los_Angeles',
    'PST': 'America/Los_Angeles',
    'EDT': 'America/New_York',
    'EST': 'America/New_York',
    'CDT': 'America/Chicago',
    'CST': 'America/Chicago',
}

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
scheduler = BackgroundScheduler()
scheduler.start()

# --- PARSERS ---
def parse_pu_time(text):
    match = re.search(r'PU:\s*(.+\d{2}:\d{2})\s+([A-Z]+)', text)
    if not match:
        return None
    datetime_str, tz_abbr = match.groups()
    try:
        full_datetime_str = f"{datetime.now().year} {datetime_str}"
        dt = datetime.strptime(full_datetime_str, "%Y %a %b %d %H:%M")
        tz_name = TIMEZONE_MAP.get(tz_abbr)
        if not tz_name:
            return None
        tz = pytz.timezone(tz_name)
        return tz.localize(dt)
    except Exception as e:
        logging.warning(f"Failed to parse PU time: {e}")
        return None

def parse_time_offset(text):
    match = re.search(r'(\d{1,2})h', text)
    if match:
        return timedelta(hours=int(match.group(1)), minutes=10)
    return None

# --- HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.caption or update.message.text or "")
    text_upper = text.upper()
    chat_id = update.message.chat_id

    pu_time = parse_pu_time(text_upper)
    offset = parse_time_offset(text_upper)

    if pu_time and offset and update.message.photo:
        file_id = update.message.photo[-1].file_id
        notify_time = pu_time - offset

        async def job():
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption="LET'S BOOK IT"
            )
            logging.info(f"Scheduled photo sent at {datetime.now()} to {chat_id}")

        scheduler.add_job(lambda: context.application.create_task(job()), 'date', run_date=notify_time)

        await update.message.reply_text("Noted", reply_to_message_id=update.message.message_id)
        logging.info(f"Scheduled job set for {notify_time}")

# --- START BOT ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & filters.Regex(r'PU:'), handle_message))

if __name__ == '__main__':
    print("📅 Scheduling Bot is running...")
    app.run_polling()

import logging
import os
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler

# ====================== CONFIG ======================

# Get bot token from environment variable
TOKEN = os.environ.get("BOT_TOKEN")

# Timezone offsets (EDT = UTC-4, PST = UTC-8, etc.)
timezone_mapping = {
    "EDT": -4, "EST": -5,
    "CDT": -5, "CST": -6,
    "MDT": -6, "MST": -7,
    "PDT": -7, "PST": -8,
}

# ====================== LOGGING ======================

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ====================== SCHEDULER ======================

scheduler = BackgroundScheduler(timezone='UTC')
scheduler.start()

# ====================== REMINDER FUNCTION ======================

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text="🚨 PLEASE BE READY, LOAD AI TIME IS CLOSE!"
    )

# ====================== MESSAGE HANDLER ======================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.caption:
        return

    lines = message.caption.strip().split("\n")
    if len(lines) < 2:
        await message.reply_text("❌ Reminder skipped.")
        return

    pu_line = lines[0].strip()
    offset_line = lines[1].strip()

    try:
        # Format: PU: Tue May 14 2025 15:30 EDT
        match = re.match(
            r"PU:\s+(\w{3}) (\w{3}) (\d{1,2}) (\d{4}) (\d{2}:\d{2}) (\w{3})",
            pu_line
        )
        if not match:
            raise ValueError("❌ Invalid PU format.")

        dow, mon, day, year, time_str, tz_abbr = match.groups()
        offset_hours, offset_minutes = 0, 0

        hour_match = re.search(r"(\d+)\s*h", offset_line)
        if hour_match:
            offset_hours = int(hour_match.group(1))
        minute_match = re.search(r"(\d+)\s*m", offset_line)
        if minute_match:
            offset_minutes = int(minute_match.group(1))

        full_time_str = f"{mon} {day} {year} {time_str}"
        local_dt = datetime.strptime(full_time_str, "%b %d %Y %H:%M")
        if tz_abbr not in timezone_mapping:
            raise ValueError("❌ Unsupported timezone.")

        utc_dt = local_dt - timedelta(hours=timezone_mapping[tz_abbr])
        reminder_time = utc_dt - timedelta(hours=offset_hours, minutes=offset_minutes)

        now_utc = datetime.utcnow()
        delay_seconds = (reminder_time - now_utc).total_seconds()

        logging.info(f"⏰ Reminder UTC: {reminder_time}")
        logging.info(f"🕒 Now UTC: {now_utc}")
        logging.info(f"⌛ Delay (s): {delay_seconds}")

        if delay_seconds <= 0:
            await message.reply_text("❌ Reminder skipped.")
            return

        scheduler.add_job(
            send_reminder,
            trigger='date',
            run_date=reminder_time,
            args=[context],
            kwargs={'job': type("job", (object,), {"chat_id": message.chat_id})}
        )

        await message.reply_text("✅ Reminder scheduled.")

    except Exception as e:
        logging.error(f"❌ Error: {e}")
        await message.reply_text("❌ Reminder skipped.")

# ====================== ERROR HANDLER ======================

def error_handler(update, context):
    logging.error(msg="Unhandled exception:", exc_info=context.error)

# ====================== MAIN ======================

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), handle_message))
    app.add_error_handler(error_handler)

    print("✅ Bot is running...")
    app.run_polling()

import logging
import os
import pytz
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Scheduler
scheduler = BackgroundScheduler(timezone='UTC')
scheduler.start()

# Timezone mapping
timezone_mapping = {
    "EDT": -4,
    "EST": -5,
    "CDT": -5,
    "CST": -6,
    "MDT": -6,
    "MST": -7,
    "PDT": -7,
    "PST": -8,
}

# Reminder function
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=context.job.chat_id, text="🚨 PLEASE BE READY, LOAD AI TIME IS CLOSE!")

# Main message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.caption:
        return

    lines = update.message.caption.strip().split("\n")
    if len(lines) < 2:
        await update.message.reply_text("❌ Reminder skipped.")
        return

    pu_line = lines[0].strip()
    offset_line = lines[1].strip()

    try:
        # Parse PU line
        match = re.match(r"PU:\s+(\w{3}) (\w{3}) (\d{1,2}) (\d{2}:\d{2}) (\w{3})", pu_line)
        if not match:
            raise ValueError("Invalid PU format.")

        dow, mon, day, time_str, tz_abbr = match.groups()
        offset_hours, offset_minutes = 0, 0

        # Parse Offset
        offset_match = re.findall(r"(\d+)\s*h", offset_line)
        if offset_match:
            offset_hours = int(offset_match[0])
        minute_match = re.findall(r"(\d+)\s*m", offset_line)
        if minute_match:
            offset_minutes = int(minute_match[0])

        # Convert PU time to UTC
        full_time_str = f"{mon} {day} {datetime.now().year} {time_str}"
        local_dt = datetime.strptime(full_time_str, "%b %d %Y %H:%M")
        if tz_abbr not in timezone_mapping:
            raise ValueError("Unsupported timezone.")
        utc_dt = local_dt - timedelta(hours=timezone_mapping[tz_abbr])
        reminder_time_utc = utc_dt - timedelta(hours=offset_hours, minutes=offset_minutes)

        now_utc = datetime.utcnow()
        delay = (reminder_time_utc - now_utc).total_seconds()

        logging.info(f"⏰ Reminder UTC: {reminder_time_utc}")
        logging.info(f"🕒 Now UTC: {now_utc}")
        logging.info(f"⌛ Delay (seconds): {delay}")

        if delay <= 0:
            await update.message.reply_text("❌ Reminder skipped.")
            return

        # Schedule reminder
        scheduler.add_job(
            send_reminder,
            trigger='date',
            run_date=reminder_time_utc,
            args=[context],
            kwargs={'job': type("obj", (object,), {"chat_id": update.message.chat_id})}
        )

        await update.message.reply_text("✅ Reminder scheduled.")

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("❌ Reminder skipped.")

# Bot runner
if __name__ == "__main__":
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(True), handle_message))

    print("✅ Bot is running...")
    app.run_polling()

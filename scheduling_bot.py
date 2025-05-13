import logging
import re
from datetime import datetime, timedelta
from pytz import timezone, utc
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# TOKEN (shaxsiy)
TOKEN = "8150025447:AAGOe4Uc3ZS2eQsmI_dsCIfRwRPxkuZF00g"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Apscheduler — eslatmalar uchun
scheduler = BackgroundScheduler()
scheduler.start()

# Reminder text
REMINDER_TEXT = "PLEASE BE READY, LOAD AI TIME IS CLOSE!"

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.caption:
        return

    caption = update.message.caption.strip()
    match = re.match(r"PU:\s+([A-Za-z]{3} [A-Za-z]{3} \d{1,2} \d{2}:\d{2}) EDT\n([\dhm\s]+)", caption)

    if not match:
        await update.message.reply_text("❌ Reminder skipped.")
        return

    pu_str, offset_str = match.groups()

    try:
        # Parse PU datetime as EDT
        pu_dt_naive = datetime.strptime(pu_str, "%a %b %d %H:%M")
        edt = timezone("America/New_York")
        pu_dt = edt.localize(pu_dt_naive)

        # Offset parsing
        offset_td = timedelta()
        for part in offset_str.split():
            if 'h' in part:
                offset_td += timedelta(hours=int(part.replace('h', '')))
            if 'm' in part:
                offset_td += timedelta(minutes=int(part.replace('m', '')))

        # Reminder time = PU - offset - 10m
        reminder_dt = pu_dt - offset_td - timedelta(minutes=10)
        reminder_utc = reminder_dt.astimezone(utc)

        now_utc = datetime.now(utc)
        if reminder_utc < now_utc:
            await update.message.reply_text("❌ Reminder skipped.")
            return

        # Schedule message
        chat_id = update.effective_chat.id

        def send_reminder():
            context.bot.send_message(chat_id=chat_id, text=REMINDER_TEXT)

        scheduler.add_job(send_reminder, trigger='date', run_date=reminder_utc)
        await update.message.reply_text("✅ Reminder scheduled.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Reminder skipped.")

# Run bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.run_polling()

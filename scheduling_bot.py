import logging
import re
from datetime import datetime, timedelta
from pytz import timezone, utc
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# TOKEN
TOKEN = "8150025447:AAGOe4Uc3ZS2eQsmI_dsCIfRwRPxkuZF00g"
bot: Bot = None  # global bot obyekt

# Logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Scheduler
scheduler = BackgroundScheduler()
scheduler.start()

REMINDER_TEXT = "PLEASE BE READY, LOAD AI TIME IS CLOSE!"

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot
    if not update.message.caption:
        return

    caption = update.message.caption.strip()

    match = re.match(
        r"PU:\s+([A-Za-z]{3})\s+([A-Za-z]{3})\s+(\d{1,2})\s+(\d{2}:\d{2})\s+EDT\s*\n?([\dhm\s]+)",
        caption,
        re.IGNORECASE
    )

    if not match:
        await update.message.reply_text("❌ Reminder skipped.")
        return

    try:
        day_str, month_str, day_num, time_str, offset_str = match.groups()
        day_str = day_str.capitalize()
        month_str = month_str.capitalize()
        this_year = datetime.now().year

        datetime_str = f"{day_str} {month_str} {int(day_num)} {time_str} {this_year}"
        pu_dt_naive = datetime.strptime(datetime_str, "%a %b %d %H:%M %Y")
        edt = timezone("America/New_York")
        pu_dt = edt.localize(pu_dt_naive)

        offset_td = timedelta()
        for part in offset_str.lower().split():
            if 'h' in part:
                offset_td += timedelta(hours=int(part.replace('h', '')))
            elif 'm' in part:
                offset_td += timedelta(minutes=int(part.replace('m', '')))

        reminder_dt = pu_dt - offset_td - timedelta(minutes=10)
        reminder_utc = reminder_dt.astimezone(utc)
        now_utc = datetime.now(utc)

        logger.info(f"📌 PU: {pu_dt}")
        logger.info(f"⏰ Reminder UTC: {reminder_utc}")
        logger.info(f"🕒 Now UTC: {now_utc}")
        logger.info(f"⌛ Delay: {(reminder_utc - now_utc).total_seconds()} sec")

        if reminder_utc < now_utc:
            await update.message.reply_text("❌ Reminder skipped.")
            return

        chat_id = update.effective_chat.id

        def send_reminder():
            logger.info(f"🔔 Sending reminder to chat {chat_id}")
            bot.send_message(chat_id=chat_id, text=REMINDER_TEXT)

        scheduler.add_job(send_reminder, trigger='date', run_date=reminder_utc)
        await update.message.reply_text("✅ Reminder scheduled.")

    except Exception as e:
        logger.error(f"Reminder error: {e}")
        await update.message.reply_text("❌ Reminder skipped.")

# Run bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    bot = app.bot  # globalga o‘tkazamiz
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.run_polling()

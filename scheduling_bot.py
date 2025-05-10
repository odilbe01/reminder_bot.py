import logging
import re
from datetime import datetime, timedelta
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
import os

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Renderdagi env orqali o'qiydi

TIMEZONE_MAP = {
    'EDT': 'America/New_York',
    'EST': 'America/New_York',
    'CDT': 'America/Chicago',
    'CST': 'America/Chicago',
    'PDT': 'America/Los_Angeles',
    'PST': 'America/Los_Angeles',
}

scheduler = BackgroundScheduler()
scheduler.start()

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- UTIL FUNCTIONS ---
def parse_pu_time(text: str):
    match = re.search(r'PU:\s*(\w+ \w+ \d+ \d{2}:\d{2})\s+(EDT|EST|CDT|CST|PDT|PST)', text)
    if not match:
        logging.warning("[!] PU time topilmadi")
        return None
    datetime_str, tz_abbr = match.groups()
    try:
        full_str = f"{datetime.now().year} {datetime_str}"
        dt = datetime.strptime(full_str, "%Y %a %b %d %H:%M")
        tz_name = TIMEZONE_MAP.get(tz_abbr)
        if tz_name:
            local_tz = pytz.timezone(tz_name)
            localized = local_tz.localize(dt)
            logging.info(f"[LOG] Parsed PU: {localized}")
            return localized
    except Exception as e:
        logging.error(f"[ERROR] parse_pu_time failed: {e}")
    return None

def parse_offset(text: str):
    h = m = 0
    h_match = re.search(r'(\d+)\s*h', text.lower())
    m_match = re.search(r'(\d+)\s*m', text.lower())
    if h_match:
        h = int(h_match.group(1))
    if m_match:
        m = int(m_match.group(1))
    logging.info(f"[LOG] Parsed Offset: {h}h {m}m")
    return timedelta(hours=h, minutes=m)

# --- MESSAGE HANDLER ---
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.caption or update.message.text or "").strip()
    chat_id = update.message.chat.id
    logging.info(f"[RECEIVED] {text}")

    pu_time = parse_pu_time(text)
    offset = parse_offset(text)

    if pu_time and offset:
        notify_time = pu_time - offset
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            logging.info(f"[LOG] file_id = {file_id}")

            async def send_reminder():
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption="📦 LET'S BOOK IT – Reminder: Load is near pickup time."
                )
                logging.info(f"[✅] Reminder sent at {datetime.now()}")

            scheduler.add_job(lambda: context.application.create_task(send_reminder()),
                              trigger='date', run_date=notify_time)

            await update.message.reply_text(f"✅ Reminder scheduled for {notify_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            await update.message.reply_text("❌ Rasm topilmadi")
    else:
        logging.warning("❌ PU yoki offset parsingda xatolik")
        await update.message.reply_text("❌ Format noto'g'ri. Iltimos, PU va vaqt offsetni tekshiring.")

# --- MAIN ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle))
    print("📡 Scheduler bot running...")
    app.run_polling()

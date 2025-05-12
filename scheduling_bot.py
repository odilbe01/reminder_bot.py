import logging, os, re, pytz, asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler

# === 1. ENV / TOKEN ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# === 2. LOGGING ===
logging.basicConfig(level=logging.INFO)

# === 3. SCHEDULER ===
scheduler = BackgroundScheduler()
scheduler.start()

# === 4. TIMEZONE MAP ===
TIMEZONE_MAP = {
    'EDT': 'America/New_York',
    'EST': 'America/New_York',
    'PDT': 'America/Los_Angeles',
    'PST': 'America/Los_Angeles',
    'CDT': 'America/Chicago',
    'CST': 'America/Chicago',
}

# === 5. PU VAQT PARSER ===
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
    except:
        return None

# === 6. OFFSET PARSER ===
def parse_offset(text: str):
    h = m = 0
    h_match = re.search(r"(\d+)\s*h", text)
    m_match = re.search(r"(\d+)\s*m", text)
    if h_match:
        h = int(h_match.group(1))
    if m_match:
        m = int(m_match.group(1))
    return timedelta(hours=h, minutes=m)

# === 7. REMINDER FUNKSIYASI ===
def schedule_reminder(application, chat_id, reply_id, remind_time):
    async def send():
        try:
            bot = application.bot
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await bot.send_message(
                chat_id=chat_id,
                text="🚨 Reminder: Load AI time is close. Please be ready.",
                reply_to_message_id=reply_id
            )
        except Exception as e:
            print("❌ Reminder error:", e)

    scheduler.add_job(lambda: asyncio.run(send()), trigger="date", run_date=remind_time)

# === 8. HANDLE MESSAGE ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.photo:
        return

    chat_id = message.chat_id
    text = (message.caption or "") + "\n" + (message.text or "")
    text_upper = text.upper()
    reply_id = message.message_id

    await context.bot.send_message(chat_id=chat_id, text="Noted")

    pu_time = parse_pu_time(text_upper)
    offset = parse_offset(text_upper)

    if pu_time and offset.total_seconds() > 0:
        remind_time = pu_time - offset - timedelta(minutes=10)
        remind_time_utc = remind_time.astimezone(pytz.utc)

        print("📌 PU:", pu_time)
        print("🕒 Offset:", offset)
        print("🕑 Reminder:", remind_time_utc)
        print("🕓 Now UTC:", datetime.now(pytz.utc))

        if remind_time_utc > datetime.now(pytz.utc):
            schedule_reminder(context.application, chat_id, reply_id, remind_time_utc)
        else:
            print("⚠️ Reminder skipped (past time)")

# === 9. START ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    print("🚛 Scheduling Bot is running...")
    app.run_polling()

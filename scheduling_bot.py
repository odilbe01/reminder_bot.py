import logging, os, re, pytz, asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, MessageHandler, ContextTypes, filters
)

# === 1. ENV / TOKEN ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# === 2. LOGGING ===
logging.basicConfig(level=logging.INFO)

# === 3. TIMEZONE MAP ===
TIMEZONE_MAP = {
    'EDT': 'America/New_York',
    'EST': 'America/New_York',
    'PDT': 'America/Los_Angeles',
    'PST': 'America/Los_Angeles',
    'CDT': 'America/Chicago',
    'CST': 'America/Chicago',
}

# === 4. PU VA OFFSET PARSER ===
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
        print("❌ PU parsing error:", e)
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

# === 5. REMINDER TASK ===
async def send_reminder(bot, chat_id, reply_id, delay_seconds):
    print(f"⏳ Sleeping for {delay_seconds} seconds")
    await asyncio.sleep(delay_seconds)
    print("⏰ Sending reminder now!")

    try:
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await bot.send_message(
            chat_id=chat_id,
            text="🚨 Reminder: Load AI time is close. Please be ready.",
            reply_to_message_id=reply_id
        )
    except Exception as e:
        print("❌ Reminder send error:", e)

# === 6. MESSAGE HANDLER ===
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
        now_utc = datetime.now(pytz.utc)

        delay = (remind_time_utc - now_utc).total_seconds()

        print("📌 PU:", pu_time)
        print("🕒 Offset:", offset)
        print("🕑 Reminder:", remind_time_utc)
        print("🕓 Now UTC:", now_utc)

        if delay > 0:
            context.application.create_task(
                send_reminder(context.bot, chat_id, reply_id, delay)
            )
        else:
            print("⚠️ Reminder skipped (past time)")

# === 7. START ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    print("🚛 Async Reminder Bot is running...")
    app.run_polling()

print(f"DEBUG: Файл запущен из {__file__}, время сборки: ВЕРСИЯ-8-FIXED")
import os
import re
import time
import datetime
import asyncio
import random
import google.generativeai as genai
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = int(os.environ.get("API_ID", 34463024))
API_HASH = os.environ.get("API_HASH", "1e0f0460d7f914c3cdb3726018c57d78")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SESSION_STRING = os.environ.get("TELETHON_SESSION", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

MOODS = ["спокойный", "веселый", "уставший", "с сарказмом"]
CURRENT_MOOD = random.choice(MOODS)

CHAT_HISTORY = {}
MAX_HISTORY = 12
LAST_BOT_MESSAGE_TIME = {}
MESSAGES_SINCE_BOT = {}
PROACTIVE_COOLDOWN_SECONDS = 3600 # Сократил для активности
MIN_MESSAGES_FOR_PROACTIVE = 6

ERROR_COUNTER = {}
USER_FORM = {}

FATE_TRIGGERS = ["бог знает", "воля бога", "воля божья", "иншаллах", "худо билади", "аллоҳ билади", "тақдир"]
TROLL_TRIGGERS = ["дурак", "тупой", "заткнись", "пошел ты", "пошёл ты", "иди нахуй", "бот ли ты", "ты бот"]

def is_working_time():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5)
    hour = now.hour
    return (9 <= hour <= 23) or (0 <= hour < 5)

def update_history(chat_id, sender_name, text):
    if chat_id not in CHAT_HISTORY: CHAT_HISTORY[chat_id] = []
    CHAT_HISTORY[chat_id].append(f"{sender_name}: {text}")
    if len(CHAT_HISTORY[chat_id]) > MAX_HISTORY: CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-MAX_HISTORY:]

def get_context(chat_id): return "\n".join(CHAT_HISTORY.get(chat_id, []))

def clean_response(text):
    text = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+", "", text)
    text = re.sub(r"[:;]\)+", "", text)
    text = re.sub(r"\)\)+", "", text)
    return text.strip()

def detect_situation(user_text):
    text_lower = user_text.lower()
    is_troll = any(trigger in text_lower for trigger in TROLL_TRIGGERS)
    has_swearing = bool(re.search(r"(нахуй|бля|ебан|хуй|пизд|сука|najas|ahmoq)", text_lower))
    return {"is_troll": is_troll or has_swearing, "has_swearing": has_swearing}

async def generate_ai_reply(chat_id, user_text, situation, address_form):
    if not GEMINI_API_KEY: return None
    try:
        # ИСПРАВЛЕНО: используем стабильную версию 1.5-flash
        model = genai.GenerativeModel("gemini-1.5-flash")
        context_text = get_context(chat_id)

        persona = f"""
Сенинг исминг Собир. Самарқандлик 25-35 ёшдаги йигитсан.
{'Сиз' if address_form == "sizlash" else "Сен"} деб мурожаат қил. 
{ 'Агар суҳбатдош қўпол бўлса, "сен"га ўт, ўткир ва кесатиқли жавоб бер.' if situation["is_troll"] else "" }
ҚАТЪИЙ ТАҚИҚ: ЭМОДЗИ ва СМАЙЛ (")" каби) ишлатма. Фақат кирилл алифбосида, қисқа жавоб бер.
"""
        prompt = f"{persona}\n\nИстория:\n{context_text}\n\nХабар: {user_text}\n\nЖавоб:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        return clean_response(response.text)
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

# ОСТАЛЬНЫЕ ЧАСТИ (proactive_loop, alisher_reply) оставь как были,
# но внутри них замени задержки на asyncio.sleep(random.uniform(0.5, 1.5)) для скорости.

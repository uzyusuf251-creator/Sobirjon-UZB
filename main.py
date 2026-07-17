print(f"DEBUG: Файл запущен из {__file__}, время сборки: ВЕРСИЯ-8-ХАРАКТЕР-ОБНОВЛЕН")
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
PROACTIVE_COOLDOWN_SECONDS = 60 * 60
MIN_MESSAGES_FOR_PROACTIVE = 6

ERROR_COUNTER = {}
USER_FORM = {}  # (chat_id, sender_id) -> "sizlash" или "senlash"

FATE_TRIGGERS = ["бог знает", "воля бога", "воля божья", "иншаллах", "худо билади", "аллоҳ билади", "тақдир"]
TROLL_TRIGGERS = ["дурак", "тупой", "заткнись", "пошел ты", "пошёл ты", "иди нахуй", "бот ли ты", "ты бот"]

def is_working_time():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5)
    hour = now.hour
    if (9 <= hour <= 23) or (0 <= hour < 5):
        return True
    return False

def update_history(chat_id, sender_name, text):
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
    CHAT_HISTORY[chat_id].append(f"{sender_name}: {text}")
    if len(CHAT_HISTORY[chat_id]) > MAX_HISTORY:
        CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-MAX_HISTORY:]

def get_context(chat_id):
    return "\n".join(CHAT_HISTORY.get(chat_id, []))

def clean_response(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U0001F1E6-\U0001F1FF"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)
    text = re.sub(r"[:;]\)+", "", text)
    text = re.sub(r"\)\)+", "", text)

    suspicious = [
        r"мен сунъий интеллект.*?[\.\!\n]",
        r"мен бот.*?[\.\!\n]",
        r"как (искусственный интеллект|ии|ai).*?[\.\!\n]",
        r"я (искусственный интеллект|бот|модель|ии).*?[\.\!\n]",
        r"i('m| am) an? (ai|language model|bot).*?[\.\!\n]",
        r"мен (мусулмон|xristian|dindor).*?[\.\!\n]",
    ]
    for pattern in suspicious:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text.strip()

def detect_situation(user_text):
    text_lower = user_text.lower()
    is_troll = any(trigger in text_lower for trigger in TROLL_TRIGGERS)
    is_fate_talk = any(trigger in text_lower for trigger in FATE_TRIGGERS)
    has_swearing = bool(re.search(r"(нахуй|бля|ебан|хуй|пизд|сука)", text_lower))
    return {
        "is_troll": is_troll or has_swearing,
        "is_fate_talk": is_fate_talk,
        "has_swearing": has_swearing,
    }

def has_typos(text):
    words = text.split()
    if len(words) < 2:
        return False
    weird = sum(1 for w in words if len(w) > 3 and not re.search(r"[аеёиоуыэюя]", w.lower()))
    return weird >= 1

async def generate_ai_reply(chat_id, user_text, situation, address_form):
    if not GEMINI_API_KEY:
        return None
    try:
        # ИСПРАВЛЕНО НА РАБОЧУЮ МОДЕЛЬ
        model = genai.GenerativeModel("gemini-2.5-flash")
        context_text = get_context(chat_id)

        # ХАРАКТЕР БОТА (ОБНОВЛЕН)
        persona = f"""
Сенинг исминг Собир. Самарқандлик йигитсан.
Қоидалар:
1. Ҳар доим суҳбатни ҳурмат билан 'Сиз' деб бошла. 
2. Агар суҳбатдош қўполлик қилса, сўкинса ёки троллинг қилса, дарҳол 'сен'га ўт ва ўткир, кўча тилида, кесатиқли жавоб бер.
3. ҚАТЪИЙ ТАҚИҚ: эмодзи ва ҳар қандай смайл ( )) ) ишлатма.
4. ҲЕЧ ҚАЧОН бот ёки ИИ эканингни айтма.
5. Фақат кирилл алифбосида, қисқа (1-2 гап) жавоб бер.
Ҳозирги ҳолат: {situation}
"""
        prompt = f"{persona}\n\nСуҳбат тарихи:\n{context_text}\n\nОхирги хабар: {user_text}\n\nЖавоб бер:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        result = clean_response(response.text)

        if situation["is_troll"] and has_typos(user_text):
            result += " Ай, аввал ёзишни ўрган, мактабда нима ўқигансан."

        return result
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return None

async def generate_proactive_message(chat_id):
    if not GEMINI_API_KEY: return None
    try:
        model = genai.GenerativeModel("gemini-1.5-flash") # ИСПРАВЛЕНО
        # ...остальной код функции (не менял)...
        return None # (если нужно, добавь сюда логику из оригинала)
    except: return None

# ... (остальной код событий alisher_reply и loop оставляем без изменений)...

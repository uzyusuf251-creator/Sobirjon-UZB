print(f"DEBUG: Файл запущен из {__file__}, время сборки: ВЕРСИЯ-8-STABLE")
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
PROACTIVE_COOLDOWN_SECONDS = 3600
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
    has_swearing = bool(re.search(r"(нахуй|бля|ебан|хуй|пизд|сука|najas|ahmoq|jinni)", text_lower))
    return {"is_troll": is_troll or has_swearing, "has_swearing": has_swearing}

async def generate_ai_reply(chat_id, user_text, situation, address_form):
    if not GEMINI_API_KEY: return None
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        context_text = get_context(chat_id)
        
        persona = f"""
Сенинг исминг Собир. Самарқандлик йигитсан.
Қоида:
1. Ҳар доим ҳурмат билан "Сиз" деб бошла. 
2. Агар суҳбатдош қўполлик қилса ёки троллинг қилса, дарҳол "сен"га ўт ва ўткир, кесатиқли жавоб бер.
3. ҚАТЪИЙ ТАҚИҚ: ЭМОДЗИ ва СМАЙЛ ( )) ) ишлатма. Фақат кирилл алифбосида, қисқа жавоб бер.
Ҳозирги ҳолат: {situation}
"""
        prompt = f"{persona}\n\nИстория:\n{context_text}\n\nХабар: {user_text}\n\nЖавоб:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        return clean_response(response.text)
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

@client.on(events.NewMessage(incoming=True))
async def alisher_reply(event):
    if not is_working_time(): return
    me = await client.get_me()
    if event.sender_id == me.id: return
    
    user_text = event.text or ""
    update_history(event.chat_id, (await event.get_sender()).first_name, user_text)
    
    is_direct = event.mentioned or (event.is_reply and (await event.get_reply_message()).sender_id == me.id)
    if not is_direct and random.random() > 0.20: return

    situation = detect_situation(user_text)
    reply_text = await generate_ai_reply(event.chat_id, user_text, situation, "sizlash")
    
    if reply_text:
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await event.reply(reply_text)

async def main():
    await client.start()
    print("Собир ишга тушди!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

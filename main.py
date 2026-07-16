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

CURRENT_MOOD = "спокойный"
CHAT_HISTORY = {}
MAX_HISTORY = 10
LAST_BOT_MESSAGE_TIME = {}
MESSAGES_SINCE_BOT = {}
PROACTIVE_COOLDOWN_SECONDS = 3600
MIN_MESSAGES_FOR_PROACTIVE = 6
ERROR_COUNTER = {}

def is_working_time():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5)
    return (9 <= now.hour <= 23) or (0 <= now.hour < 5)

def clean_response(text):
    # Удаление эмодзи
    text = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+", "", text)
    # Удаление скобок (смайликов типа )) или (( )
    text = re.sub(r"[\)\(]+", "", text)
    return text.strip()

async def generate_ai_reply(chat_id, user_text, situation):
    if not GEMINI_API_KEY: return None
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        persona = f"""
Сенинг исминг Собир. Самарқандлик оддий йигитсан. 
Қоидалар:
1. Ҳар доим суҳбатни "Сиз" деб бошла. 
2. Агар суҳбатдош қўполлик қилса, сўкинса ёки ҳақоратласа, дарҳол "сен"га ўт ва ўткир, кўча тилида, Самарқанд шевасида жавоб бер.
3. ЭМОДЗИ ва ҚАВС ( )) ) ишлатиш қатъиян тақиқланади.
4. ҲЕЧ ҚАЧОН бот ёки ИИ эканингни айтма.
5. Жавоблар қисқа, фақат кирилл алифбосида.
Ҳозирги ҳолат: {situation}
"""
        prompt = f"{persona}\n\nХабар: {user_text}\n\nЖавоб бер:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        return clean_response(response.text)
    except Exception as e:
        print(f"Ошибка: {e}")
        return "нима deyapsan, tushunmadim"

@client.on(events.NewMessage(incoming=True))
async def alisher_reply(event):
    if not is_working_time(): return
    me = await client.get_me()
    if event.sender_id == me.id: return

    user_text = event.text or ""
    is_direct = event.mentioned or (event.is_reply and (await event.get_reply_message()).sender_id == me.id)
    
    if not is_direct and random.random() > 0.20: return

    # Определяем тон
    has_swearing = bool(re.search(r"(нахуй|бля|ебан|хуй|пизд|сука)", user_text.lower()))
    situation = "агрессив" if has_swearing else "дўстона"

    reply_text = await generate_ai_reply(event.chat_id, user_text, situation)
    
    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(random.uniform(2.0, 4.0))
        await event.reply(reply_text)

async def main():
    await client.start()
    print("Собир ишга тушди!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

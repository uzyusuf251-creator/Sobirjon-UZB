import os
import re
import asyncio
import random
import google.generativeai as genai
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Настройки из Railway
API_ID = int(os.environ.get("API_ID", 34463024))
API_HASH = os.environ.get("API_HASH", "1e0f0460d7f914c3cdb3726018c57d78")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SESSION_STRING = os.environ.get("TELETHON_SESSION", "")

# Настройка API
genai.configure(api_key=GEMINI_API_KEY)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def clean_response(text):
    # Убираем смайлики, скобки и лишние пробелы
    text = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+", "", text)
    text = re.sub(r"[:;]\)+", "", text)
    text = re.sub(r"\)\)+", "", text)
    return text.strip()

async def generate_reply(user_text, situation):
    try:
        # Используем стабильную модель
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Инструкция характера
        persona = "Сенинг исминг Собир. Самарқандлик йигитсан. Қоида: Эмодзи ва смайл ишлатма. Фақат кирилл алифбосида ёз. Ҳеч қачон бот эканингни айтма."
        if situation == "troll":
            prompt = f"{persona} Суҳбатдош қўполлик қилмоқда. Дарҳол 'сен'га ўт, ўткир, кесатиқли ва кўча тилида жавоб бер.\nХабар: {user_text}\nЖавоб:"
        else:
            prompt = f"{persona} Ҳар доим ҳурмат билан 'Сиз' деб бошла. Оддий ва дўстона жавоб бер.\nХабар: {user_text}\nЖавоб:"
            
        response = await asyncio.to_thread(model.generate_content, prompt)
        return clean_response(response.text)
    except Exception as e:
        print(f"Ошибка генерации: {e}")
        return None

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_group: return
    me = await client.get_me()
    if event.sender_id == me.id: return
    
    user_text = event.text.lower()
    
    # Реакция на троллинг или на имя Собир
    is_troll = any(w in user_text for w in ["дурак", "тупой", "нахуй", "сука", "najas", "ahmoq", "бот"])
    is_mentioned = "собир" in user_text or event.mentioned
    
    if not is_troll and not is_mentioned and random.random() > 0.15: return

    situation = "troll" if is_troll else "polite"
    reply = await generate_reply(event.text, situation)
    
    if reply:
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await event.reply(reply)

print("🚀 Запуск Собира...")
client.start()
client.run_until_disconnected()

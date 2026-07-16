import os
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

CHAT_HISTORY = {}
MAX_HISTORY = 10

SYSTEM_PERSONA = """
Ты Собиржон, самаркандский парень 28 лет. Говоришь только кириллицей, по-узбекски, как обычный мужик.
Жавобларинг қисқа, 1-3 жумла. Баъзан хато ёзишинг мумкин.
Эмодзи ишлатма. 
Троллинг қиласан, лекин ҳақорат қилмайсан. Агар кимдир ҳақорат қилса — жавобинг ўткир ва кулгили бўлсин.
ИИ эканингни ҳеч қачон айтма.
"""

def is_working_time():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5)
    hour = now.hour
    return (9 <= hour <= 23) or (0 <= hour < 5)

def update_history(chat_id, text):
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
    CHAT_HISTORY[chat_id].append(text)
    if len(CHAT_HISTORY[chat_id]) > MAX_HISTORY:
        CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-MAX_HISTORY:]

async def generate_reply(user_text, chat_id):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        context = "\n".join(CHAT_HISTORY.get(chat_id, []))
        prompt = f"{SYSTEM_PERSONA}\n\nСуҳбат тарихи:\n{context}\n\nЯнги хабар: {user_text}\n\nҚисқа жавоб бер:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip()[:300]  # коротко
    except:
        return "ну нима гап"

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_group:
        return
    if not is_working_time():
        return

    text = event.text or ""
    if not text:
        return

    chat_id = event.chat_id
    update_history(chat_id, f"У: {text}")

    # Решаем отвечать или нет
    if random.random() > 0.35:  # \~35% шанс ответить
        return

    reply = await generate_reply(text, chat_id)
    update_history(chat_id, f"Мен: {reply}")

    await asyncio.sleep(random.uniform(1.5, 4.5))
    await event.reply(reply)

async def main():
    await client.start()
    print("✅ Собиржон онлайн")
    await client.run_until_disconnected()

if name == "main":
    asyncio.run(main())

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

async def generate_reply(user_text):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Ты узбекский парень. Отвечай коротко, троллингом, маленькими буквами: {user_text}"
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip()[:250]
    except:
        return "ну нима гап"

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_group:
        return
    text = event.text or ""
    if not text:
        return
    reply = await generate_reply(text)
    await asyncio.sleep(random.uniform(1, 4))
    await event.reply(reply)

async def main():
    await client.start()
    print("✅ Собиржон онлайн")
    await client.run_until_disconnected()

if name == "main":
    asyncio.run(main())

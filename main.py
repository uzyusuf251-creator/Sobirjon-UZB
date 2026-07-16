print(f"DEBUG: Файл запущен из {__file__}, время сборки: ВЕРСИЯ-2")
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
CURRENT_MODE = "soft"

def is_working_time():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)
    hour = now.hour
    if (9 <= hour <= 23) or (0 <= hour < 5):
        return True
    return False

async def generate_ai_reply(user_text, mode):
    if not GEMINI_API_KEY:
        return "Извини, сейчас не могу ответить осмысленно."
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"Ответь коротко и по-дружески на сообщение (стиль общения: {mode}): {user_text}"
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Ошибка генерации ответа: {e}")
        return "Что-то я задумался, повтори ещё раз?"

@client.on(events.NewMessage(incoming=True))
async def alisher_reply(event):
    global CURRENT_MODE
    print(f"📩 Получено сообщение: is_group={event.is_group}, text={event.text}")
    if not event.is_group:
        print("❌ Не группа, пропускаю")
        return
    if not is_working_time():
        print("❌ Не рабочее время, пропускаю")
        return
    sender = await event.get_sender()
    me = await client.get_me()
    if sender and sender.id == me.id:
        print("❌ Это моё собственное сообщение, пропускаю")
        return
    should_reply = (
        event.mentioned
        or (event.is_reply and (await event.get_reply_message()).sender_id == me.id)
        or (random.random() < 0.15)
    )
    print(f"🤔 should_reply = {should_reply}")
    if should_reply:
        user_text = event.text or ""
        reply_text = await generate_ai_reply(user_text, CURRENT_MODE)
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(2.0, 4.5))
            await event.reply(reply_text)

async def main():
    print("🚀 Запуск клиента...")
    await client.start()
    print("✅ Client started")
    print("Авторизован ли пользователь?", await client.is_user_authorized())
    me = await client.get_me()
    print("Это аккаунт:", me.username or me.first_name)
    print("✅ Алишер полностью готов к работе!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

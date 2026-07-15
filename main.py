import os
import datetime
import asyncio
import random
import google.generativeai as genai
from telethon import TelegramClient, events

# Получаем данные из переменных
API_ID = int(os.environ.get("API_ID", 34463024))
API_HASH = os.environ.get("API_HASH", "1e0f0460d7f914c3cdb3726018c57d78")
GEMINI_API_KEY = os.environ.get("AQ.Ab8RN6LuakSR2vaGMrhW7DbXASLTf1yfhvuEyHVUzCcUCNqjfg", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

client = TelegramClient('alisher_session', API_ID, API_HASH)
CURRENT_MODE = "soft"

# Функция нового графика: работает с 09:00 до 05:00
def is_working_time():
    now = datetime.datetime.now()
    hour = now.hour
    # Если время от 09:00 до 23:59 ИЛИ от 00:00 до 04:59
    if (9 <= hour <= 23) or (0 <= hour < 5):
        return True
    return False

# ... (остальной код функции generate_ai_reply и обработчики команд остаются прежними)

# Исправленная функция автоответчика
@client.on(events.NewMessage(incoming=True))
async def alisher_reply(event):
    global CURRENT_MODE
    if not event.is_group:
        return
        
    # Проверка нового графика
    if not is_working_time():
        return

    sender = await event.get_sender()
    me = await client.get_me()
    if sender and sender.id == me.id:
        return

    should_reply = event.mentioned or (event.is_reply and (await event.get_reply_message()).sender_id == me.id) or (random.random() < 0.15)

    if should_reply:
        user_text = event.text or ""
        reply_text = await generate_ai_reply(user_text, CURRENT_MODE)
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(2.0, 4.5))
            await event.reply(reply_text)

# ... (оставшаяся часть кода: async def main и if __name__ == '__main__' как были ранее)

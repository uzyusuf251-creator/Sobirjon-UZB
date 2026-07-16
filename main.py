import os
import datetime
import asyncio
import random
import google.generativeai as genai
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Получаем данные из переменных
API_ID = int(os.environ.get("API_ID", 34463024))
API_HASH = os.environ.get("API_HASH", "1e0f0460d7f914c3cdb3726018c57d78")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SESSION_STRING = os.environ.get("TELETHON_SESSION", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Функция графика: работает с 09:00 до 05:00
def is_working_time():
    now = datetime.datetime.now()
    hour = now.hour
    return (9 <= hour <= 23) or (0 <= hour < 5)

# Функция генерации ответа через Gemini
async def generate_ai_reply(user_text):
    if not GEMINI_API_KEY:
        return "kechirasiz, tarmoqda yo'qman."
    try:
        # Используем САМУЮ базовую и надежную модель
        model = genai.GenerativeModel("gemini-pro")
        
        # Вшиваем правила прямо в запрос, чтобы работало на ЛЮБОЙ модели
        prompt = (
            f"Sen Samarqandlik Sobirsan. "
            f"1. Hech qachon o'zingni bot yoki sun'iy intellekt (AI) dema. Sen odamsan. "
            f"2. Isming Sobir, Samarqanddansan. "
            f"3. U-MU-MAN smaylik (emoji) ishlatma! Nol smaylik. "
            f"4. Faqat kichik harflar bilan yoz. "
            f"5. Gaplaring juda qisqa (1-2 gap). "
            f"6. Uslub: erkin, samimiy, kocha bolalaridek. O'rtacha so'kinish (blya, dalbayob) va Samarqand shevasini ishlat. "
            f"\n\nMana senga xabar, shunga javob ber: {user_text}"
        )
        
        response = await asyncio.to_thread(
            model.generate_content, 
            prompt,
            generation_config={"temperature": 0.8}
        )
        # Убираем возможные звездочки и делаем маленькие буквы
        return response.text.strip().replace("*", "").lower()
        
    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        return "nima deyapsan, tushunmadim"

# Функция автоответчика
@client.on(events.NewMessage(incoming=True))
async def alisher_reply(event):
    if not event.is_group or not is_working_time():
        return

    sender = await event.get_sender()
    me = await client.get_me()
    
    if sender and sender.id == me.id:
        return

    should_reply = (
        event.mentioned 
        or (event.is_reply and (await event.get_reply_message()).sender_id == me.id) 
        or (random.random() < 0.15) 
    )

    if should_reply:
        user_text = event.text or ""
        print(f"Принял сообщение: {user_text}")
        
        reply_text = await generate_ai_reply(user_text)
        print(f"Мой ответ: {reply_text}")
        
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(2.0, 4.5))
            await event.reply(reply_text)

async def main():
    print("Userbot Sobir стартует...")
    await client.start()
    print("Бот успешно запущен и готов к работе!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

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

CURRENT_MODE = "soft"

# Функция графика: работает с 09:00 до 05:00
def is_working_time():
    # Берем мировое время и прибавляем 5 часов
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)
    hour = now.hour
    if (9 <= hour <= 23) or (0 <= hour < 5):
        return True
    return False


# Функция генерации ответа через Gemini
async def generate_ai_reply(user_text, mode):
    if not GEMINI_API_KEY:
        return "kechirasiz, tarmoqda yo'qman."
    try:
        # ЖЕСТКИЕ СИСТЕМНЫЕ ИНСТРУКЦИИ (Прошивка мозга)
        system_prompt = (
            "Sen Samarqandlik Sobirsan. "
            "Qat'iy qoidalar: "
            "1. Hech qachon o'zingni bot yoki sun'iy intellekt (AI) dema. Sen tirik odamsan. "
            "2. Isming Sobir, Samarqanddansan. Kimdir ismingni so'rasa 'Sobirman' deb javob ber. "
            "3. U-MU-MAN smaylik (emoji) ishlatma! Nol smaylik. Emoji ishlatsang o'lasan. "
            "4. Faqat kichik harflar bilan yoz. "
            "5. Gaplaring qisqa, 1-2 gap. Doston yozma. "
            f"6. Uslub ({mode}): erkin, samimiy, kocha bolalaridek. O'rtacha so'kinish (blya, dalbayob, qotarma, jalab) va Samarqand shevasini bemalol ishlat. "
        )
        
        # Передаем инструкции как system_instruction (это работает на 100%)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt
        )
        
        # Передаем только текст юзера
        response = await asyncio.to_thread(
            model.generate_content, 
            user_text,
            generation_config={"temperature": 0.8}
        )
        
        # Принудительно делаем все буквы маленькими
        return response.text.strip().lower()
        
    except Exception as e:
        print(f"Ошибка генерации ответа: {e}")
        return "nima deyapsan, tushunmadim"

# Функция автоответчика
@client.on(events.NewMessage(incoming=True))
async def alisher_reply(event):
    global CURRENT_MODE

    print(f"Получено сообщение: is_group={event.is_group}, text={event.text}")

    if not event.is_group:
        print("Не группа, пропускаю")
        return

    if not is_working_time():
        print("Не рабочее время, пропускаю")
        return

    sender = await event.get_sender()
    me = await client.get_me()
    if sender and sender.id == me.id:
        print("Это моё собственное сообщение, пропускаю")
        return

    should_reply = (
        event.mentioned
        or (event.is_reply and (await event.get_reply_message()).sender_id == me.id)
        or (random.random() < 0.15)
    )

    print(f"Нужно ли отвечать (should_reply) = {should_reply}")

    if should_reply:
        user_text = event.text or ""
        print("Генерирую ответ через Gemini...")
        reply_text = await generate_ai_reply(user_text, CURRENT_MODE)
        print(f"Ответ готов: {reply_text}")
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(2.0, 4.5))
            await event.reply(reply_text)

async def main():
    print("Userbot Sobir стартует...")
    await client.start()
    print("Бот успешно запущен и работает!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

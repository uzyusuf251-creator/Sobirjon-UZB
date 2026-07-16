import os
import asyncio
import random
import warnings
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Скрываем предупреждение от Google, чтобы не засорять консоль
warnings.filterwarnings("ignore")
import google.generativeai as genai

# Получаем данные из переменных
API_ID = int(os.environ.get("API_ID", 34463024))
API_HASH = os.environ.get("API_HASH", "1e0f0460d7f914c3cdb3726018c57d78")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SESSION_STRING = os.environ.get("TELETHON_SESSION", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

CURRENT_MODE = "soft"

# Функция генерации ответа через Gemini
async def generate_ai_reply(user_text, mode):
    if not GEMINI_API_KEY:
        return "kechirasiz, tarmoqda yo'qman."
    try:
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
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt
        )
        
        response = await asyncio.to_thread(
            model.generate_content, 
            user_text,
            generation_config={"temperature": 0.8}
        )
        return response.text.strip().lower()
        
    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        return "nima deyapsan, tushunmadim"

# Функция автоответчика
@client.on(events.NewMessage(incoming=True))
async def alisher_reply(event):
    global CURRENT_MODE

    sender = await event.get_sender()
    me = await client.get_me()
    
    # Не отвечаем на свои собственные сообщения
    if sender and sender.id == me.id:
        return

    should_reply = False

    # ЛОГИКА: Когда отвечать?
    if event.is_private:
        # В личных сообщениях отвечаем ВСЕГДА
        should_reply = True
    elif event.is_group:
        # В группе отвечаем, только если нас тегнули или ответили на наше сообщение
        if event.mentioned or (event.is_reply and (await event.get_reply_message()).sender_id == me.id):
            should_reply = True

    if should_reply:
        user_text = event.text or ""
        print(f"💬 Принял сообщение: {user_text}")
        
        reply_text = await generate_ai_reply(user_text, CURRENT_MODE)
        print(f"✅ Мой ответ: {reply_text}")
        
        async with client.action(event.chat_id, 'typing'):
            await asyncio.sleep(random.uniform(2.0, 4.0))
            await event.reply(reply_text)

async def main():
    print("🚀 Userbot Sobir стартует...")
    await client.start()
    print("✅ Бот успешно запущен и готов к работе!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

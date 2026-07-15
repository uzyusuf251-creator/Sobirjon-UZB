import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Получаем переменные окружения
api_id = int(os.getenv("API_ID", 34463024))
api_hash = os.getenv("API_HASH", "1e0f0460d7f914c3cdb3726018c57d78")
session_string = os.getenv("TELETHON_SESSION") or os.getenv("SESSION_STRING")

# Безопасная инициализация: если строки сессии нет или она битая, создаем обычный файл сессии
if session_string and len(session_string.strip()) > 50:
    print("🔑 Найдена строка сессии, используем StringSession...")
    client = TelegramClient(StringSession(session_string.strip()), api_id, api_hash)
else:
    print("📁 Строка сессии не найдена или неверна. Используем файл сессии alisher_session...")
    client = TelegramClient('alisher_session', api_id, api_hash)

@client.on(events.NewMessage)
async def handler(event):
    if event.is_group and not event.out:   # Только в группах, не свои сообщения
        text = event.message.message.lower()
        if any(word in text for word in ["привет", "салам", "аборт", "бог", "хадис", "коран", "аллах"]):
            await event.reply("блин, хорошая тема 😂 щас нормально отвечу.")
        else:
            # Пока редко отвечает, чтобы не спамил
            if "алишер" in text:
                await event.reply("я здесь, брат. что обсуждаем?")

async def main():
    print("🚀 Алишер Userbot стартует...")
    await client.start()
    print("✅ Алишер успешно запущен и работает!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

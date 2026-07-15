import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_string = os.getenv("TELETHON_SESSION")

client = TelegramClient(StringSession(session_string), api_id, api_hash)

@client.on(events.NewMessage)
async def handler(event):
    if event.is_group and not event.out:   # Только в группах, не свои сообщения
        text = event.message.message.lower()
        if any(word in text for word in ["привет", "салам", "аборт", "бог", "хадис", "коран", "аллах"]):
            await event.reply("Блин, хорошая тема 😂 Щас нормально отвечу.")
        else:
            # Пока редко отвечает, чтобы не спамил
            if "алишер" in text:
                await event.reply("Я здесь, брат. Что обсуждаем?")

async def main():
    print("🚀 Алишер Userbot стартует...")
    await client.start()
    print("✅ Алишер успешно запущен и работает!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

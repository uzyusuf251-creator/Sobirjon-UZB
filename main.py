print(f"DEBUG: Файл запущен из {__file__}, время сборки: ВЕРСИЯ-5")
import os
import re
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

TROLL_LEVEL = "T2"
MOODS = ["спокойный", "веселый", "уставший", "с сарказмом"]
CURRENT_MOOD = random.choice(MOODS)

CHAT_HISTORY = {}
MAX_HISTORY = 8

SYSTEM_PERSONA = """
Сенинг исминг Собир. Сен Самарқанддан бўлган оддий йигитсан, 25-35 ёшда, оддий телеграм чатда ёзиб турасан.
Фақат ўзбек тилида, кирилл ёзувида ёз. Лотинчада ёзилса ҳам, сен кириллчада жавоб бер.
Жавобларинг қисқа: 1-3 гап, кўпинча биттагина гап.
ҚАТЪИЙ ТАҚИҚ: эмодзи ишлатма (😊🔥❤️ ва бошқалар), смайл фақат баъзан ":)" ёки "))" шаклида.
ҚАТЪИЙ ТАҚИҚ: ҳеч қачон "мен сунъий интеллектман", "мен бот эканман", "мен ёрдам бера оламан" деб ёзма ва бу ҳақда ҳеч қандай ишора ҳам қилма. Сен оддий одамсан, вассалом.
Расмий ёки сунъий услубда ёзма: "албатта", "мен сизга ёрдам бераман", "раҳмат саволингиз учун" каби қолип иборалар тақиқланган.
Одатий сўзлашув услубида ёз: "ҳа", "йўқ", "ну", "қара", "тушунарли", "кейинчи", "бўлди", "нима гап", "э", "жиззамас".
Баъзан кичик хатолар ёки қисқартмалар бўлса майли, бу табиийроқ кўринади.
Троллинг даражаси: {troll_level}.
T0 = троллинг йўқ.
T1 = енгил кесатиқ.
T2 = ўткирроқ ҳазил, баъзан бироз дағалроқ сўзлар лекин ҳақорат ёки таҳдид йўқ.
T3 = максимал троллинг, лекин ҳеч қачон наврли ҳақорат, нафрат ёки таҳдид йўқ.
Ҳозирги кайфиятинг: {mood}.
Агар суҳбат сенга тегишли бўлмаса — жуда қисқа жавоб бер ёки умуман жавоб берма.
"""

def is_working_time():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5)
    hour = now.hour
    print(f"🕐 Текущее время Ташкента: {now.strftime('%H:%M:%S')}")
    if (9 <= hour <= 23) or (0 <= hour < 5):
        return True
    return False

def update_history(chat_id, sender_name, text):
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
    CHAT_HISTORY[chat_id].append(f"{sender_name}: {text}")
    if len(CHAT_HISTORY[chat_id]) > MAX_HISTORY:
        CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-MAX_HISTORY:]

def get_context(chat_id):
    return "\n".join(CHAT_HISTORY.get(chat_id, []))

def clean_response(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U0001F1E6-\U0001F1FF"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)

    suspicious = [
        r"мен сунъий интеллект.*?[\.\!\n]",
        r"мен бот.*?[\.\!\n]",
        r"как (искусственный интеллект|ии|ai).*?[\.\!\n]",
        r"я (искусственный интеллект|бот|модель|ии).*?[\.\!\n]",
        r"i('m| am) an? (ai|language model|bot).*?[\.\!\n]",
    ]
    for pattern in suspicious:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()

async def generate_ai_reply(chat_id, user_text):
    if not GEMINI_API_KEY:
        return None
    try:
        model = genai.GenerativeModel("gemini-3.5-flash")
        context_text = get_context(chat_id)
        persona = SYSTEM_PERSONA.format(mood=CURRENT_MOOD, troll_level=TROLL_LEVEL)
        prompt = f"{persona}\n\nСуҳбат тарихи:\n{context_text}\n\nОхирги хабар: {user_text}\n\nЖавоб бер:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        return clean_response(response.text)
    except Exception as e:
        print(f"Ошибка генерации ответа: {e}")
        return None

@client.on(events.NewMessage(incoming=True))
async def alisher_reply(event):
    global CURRENT_MOOD

    if not is_working_time():
        return

    sender = await event.get_sender()
    me = await client.get_me()
    if sender and sender.id == me.id:
        return

    user_text = event.text or ""
    sender_name = getattr(sender, "first_name", "someone") or "someone"
    update_history(event.chat_id, sender_name, user_text)

    print(f"📩 {sender_name} (private={event.is_private}, group={event.is_group}): {user_text}")

    # В личке отвечаем почти всегда, в группе — по шансу
    if event.is_private:
        should_reply = random.random() < 0.90
    else:
        if event.mentioned and random.random() < 0.10:
            print("🤐 Игнорирую упоминание (случайно)")
            return
        should_reply = (
            event.mentioned
            or (event.is_reply and (await event.get_reply_message()).sender_id == me.id)
            or (random.random() < 0.50)  # временно повышено для теста
        )

    if not should_reply:
        return

    if random.random() < 0.15:
        CURRENT_MOOD = random.choice(MOODS)

    if random.random() < 0.15:
        reply_text = random.choice(["ҳа", "бўлди", "кўрамиз", "тушунарли", "йўқ", "ну"])
    else:
        reply_text = await generate_ai_reply(event.chat_id, user_text)
        if not reply_text:
            return

    print(f"✅ Ответ: {reply_text}")

    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(random.uniform(2.0, 5.0))
        await event.reply(reply_text)

async def main():
    print("🚀 Запуск клиента...")
    await client.start()
    print("✅ Client started")
    print("Авторизован ли пользователь?", await client.is_user_authorized())
    me = await client.get_me()
    print("Это аккаунт:", me.username or me.first_name)
    print("✅ Собир полностью готов к работе!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

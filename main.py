print(f"DEBUG: Файл запущен из {__file__}, время сборки: ВЕРСИЯ-8")
import os
import re
import time
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

MOODS = ["спокойный", "веселый", "уставший", "с сарказмом"]
CURRENT_MOOD = random.choice(MOODS)

CHAT_HISTORY = {}
MAX_HISTORY = 12

LAST_BOT_MESSAGE_TIME = {}
MESSAGES_SINCE_BOT = {}
PROACTIVE_COOLDOWN_SECONDS = 60 * 60
MIN_MESSAGES_FOR_PROACTIVE = 6

ERROR_COUNTER = {}
USER_FORM = {}  # (chat_id, sender_id) -> "sizlash" или "senlash"

FATE_TRIGGERS = ["бог знает", "воля бога", "воля божья", "иншаллах", "худо билади", "аллоҳ билади", "тақдир"]
TROLL_TRIGGERS = ["дурак", "тупой", "заткнись", "пошел ты", "пошёл ты", "иди нахуй", "бот ли ты", "ты бот"]

def is_working_time():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5)
    hour = now.hour
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
    # Убираем эмодзи
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U0001F1E6-\U0001F1FF"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)

    # Полностью убираем скобочки-смайлики )) и :)
    text = re.sub(r"[:;]\)+", "", text)
    text = re.sub(r"\)\)+", "", text)

    suspicious = [
        r"мен сунъий интеллект.*?[\.\!\n]",
        r"мен бот.*?[\.\!\n]",
        r"как (искусственный интеллект|ии|ai).*?[\.\!\n]",
        r"я (искусственный интеллект|бот|модель|ии).*?[\.\!\n]",
        r"i('m| am) an? (ai|language model|bot).*?[\.\!\n]",
        r"мен (мусулмон|xristian|dindor).*?[\.\!\n]",
    ]
    for pattern in suspicious:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()

def detect_situation(user_text):
    text_lower = user_text.lower()
    is_troll = any(trigger in text_lower for trigger in TROLL_TRIGGERS)
    is_fate_talk = any(trigger in text_lower for trigger in FATE_TRIGGERS)
    has_swearing = bool(re.search(r"(нахуй|бля|ебан|хуй|пизд|сука)", text_lower))
    return {
        "is_troll": is_troll or has_swearing,
        "is_fate_talk": is_fate_talk,
        "has_swearing": has_swearing,
    }

def has_typos(text):
    words = text.split()
    if len(words) < 2:
        return False
    weird = sum(1 for w in words if len(w) > 3 and not re.search(r"[аеёиоуыэюя]", w.lower()))
    return weird >= 1

async def generate_ai_reply(chat_id, user_text, situation, address_form):
    if not GEMINI_API_KEY:
        return None
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        context_text = get_context(chat_id)

        address_instruction = (
            "Суҳбатдошга 'Сиз' деб, ҳурмат билан мурожаат қил."
            if address_form == "sizlash"
            else "Суҳбатдошга 'сен' деб, оддий тарзда мурожаат қил."
        )

        tone_instruction = "Оддий, самимий ва дўстона тарзда жавоб бер, троллинг қилма."
        if situation["has_swearing"]:
            tone_instruction = (
                "Суҳбатдош сенга дағал сўзлар билан ёзди ёки сени жойингга юборди. "
                "Хафа бўлма, аксинча кулиб жавоб бер, 'хахаха' каби кулги қўш, ҳазиллаш."
            )
        elif situation["is_troll"]:
            tone_instruction = (
                "Суҳбатдош сени троллламоқчи ёки калака қилмоқчи. "
                "Сен ҳам ўткирроқ, кесатиқли жавоб бер, лекин ҳақорат ёки таҳдидга ўтма."
            )
        elif situation["is_fate_talk"]:
            tone_instruction = (
                "Суҳбатдош 'худо билади', 'тақдир' каби гап айтди. "
                "Табиий тарзда, енгил шубҳа билан савол бер."
            )

        persona = f"""
Сенинг исминг Собир. Сен Самарқанддан бўлган оддий йигитсан, 25-35 ёшда, оддий телеграм чатда ёзиб турасан.
Фақат ўзбек тилида, кирилл ёзувида ёз. Лотинчада ёзилса ҳам, сен кириллчада жавоб бер.
Жавобларинг қисқа: 1-3 гап, кўпинча биттагина гап.
ҚАТЪИЙ ТАҚИҚ: эмодзи ва смайл ишлатма (")" каби скобка-смайл ҳам, эмодзи ҳам МУТЛАҚО ишлатма).
ҲЕЧ ҚАЧОН ўзингнинг диний эътиқодинг ҳақида гапирма.
ҲЕЧ ҚАЧОН "мен сунъий интеллектман", "мен бот эканман" деб ёзма.
Расмий услубда ёзма: "албатта", "мен сизга ёрдам бераман" каби қолип иборалар тақиқланган.
Одатий сўзлашув услубида ёз: "ҳа", "йўқ", "ну", "қара", "тушунарли", "кейинчи", "бўлди", "нима гап", "э".
Ҳозирги кайфиятинг: {CURRENT_MOOD}.
{address_instruction}
МУҲИМ: Жавобинг суҳбат мавзусига мос бўлсин, суҳбат тарихини инобатга ол.

{tone_instruction}
"""

        prompt = f"{persona}\n\nСуҳбат тарихи:\n{context_text}\n\nОхирги хабар: {user_text}\n\nЖавоб бер:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        result = clean_response(response.text)

        if situation["is_troll"] and has_typos(user_text):
            counter = ERROR_COUNTER.get(chat_id, 0) + 1
            ERROR_COUNTER[chat_id] = counter
            if counter % random.choice([2, 3]) == 0:
                result += " Ай, аввал ёзишни ўрган, мактабда нима ўқигансан."

        return result
    except Exception as e:
        print(f"⚠️ Ошибка генерации ответа (пропускаю без ответа): {e}")
        return None

async def generate_proactive_message(chat_id):
    if not GEMINI_API_KEY:
        return None
    try:
        model = genai.GenerativeModel("gemini-3.5-flash")
        context_text = get_context(chat_id)
        if not context_text or len(context_text.strip()) < 20:
            return None  # недостаточно контекста, чтобы говорить по теме

        persona = f"""
Сенинг исминг Собир, Самарқанддан. Фақат ўзбек тилида, кирилл ёзувида ёз. Жуда қисқа гапир (1-2 гап).
ЭМОДЗИ ва смайл ")" ишлатма. Диний эътиқодинг ҳақида гапирма. ИИ/бот эканингни айтма.
Ҳозирги кайфиятинг: {CURRENT_MOOD}.

ЖУДА МУҲИМ: Қуйида чатдаги сўнгги хабарларни ЎҚИ ва аниқ шу МАВЗУ бўйича фикр ёки savol yoz.
Мавзуга умуман алоқаси йўқ, тасодифий гап (масалан "мен дам олгани кетяпман", "сен нима қиляпсан" каби умумий гаплар) ЁЗМА.
Агар чатдаги хабарлардан аниқ мавзуни туша олмасанг — ҳеч нарса ёзма, бўш жавоб қайтар.
"""
        prompt = (
            f"{persona}\n\nЧатдаги сўнгги хабарлар:\n{context_text}\n\n"
            f"Юқоридаги хабарларда аниқ қандай мавзу муҳокама қилинмоқда? "
            f"Шу мавзу бўйича ўзингнинг фикринг ёки саволингни ёз (агар мавзу аниқ бўлмаса, бўш қатор қайтар)."
        )
        response = await asyncio.to_thread(model.generate_content, prompt)
        result = clean_response(response.text)
        if not result or len(result.strip()) < 5:
            return None
        return result
    except Exception as e:
        print(f"Ошибка генерации проактивного сообщения: {e}")
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

    MESSAGES_SINCE_BOT[event.chat_id] = MESSAGES_SINCE_BOT.get(event.chat_id, 0) + 1

    print(f"📩 {sender_name} (private={event.is_private}, group={event.is_group}): {user_text}")

    is_direct = False
    if event.is_private:
        should_reply = True
        is_direct = True
    else:
        is_reply_to_bot = event.is_reply and (await event.get_reply_message()).sender_id == me.id
        if event.mentioned or is_reply_to_bot:
            should_reply = True
            is_direct = True
        else:
            should_reply = random.random() < 0.50

    if not should_reply:
        return

    if random.random() < 0.15:
        CURRENT_MOOD = random.choice(MOODS)

    situation = detect_situation(user_text)

    user_key = (event.chat_id, sender.id)
    if user_key not in USER_FORM:
        USER_FORM[user_key] = "sizlash"
    if situation["is_troll"]:
        USER_FORM[user_key] = "senlash"
    address_form = USER_FORM[user_key]

    if not is_direct and not situation["is_troll"] and not situation["is_fate_talk"] and random.random() < 0.15:
        reply_text = random.choice(["ҳа", "бўлди", "кўрамиз", "тушунарли", "йўқ", "ну"])
    else:
        reply_text = await generate_ai_reply(event.chat_id, user_text, situation, address_form)
        if not reply_text:
            # Тихо пропускаем, никаких фраз-заглушек
            return

    print(f"✅ Ответ: {reply_text}")

    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(random.uniform(2.0, 5.0))
        await event.reply(reply_text)

    LAST_BOT_MESSAGE_TIME[event.chat_id] = time.time()
    MESSAGES_SINCE_BOT[event.chat_id] = 0

async def proactive_loop():
    while True:
        await asyncio.sleep(random.randint(600, 1200))

        if not is_working_time():
            continue

        for chat_id, history in list(CHAT_HISTORY.items()):
            last_time = LAST_BOT_MESSAGE_TIME.get(chat_id, 0)
            since_bot = MESSAGES_SINCE_BOT.get(chat_id, 0)

            if time.time() - last_time < PROACTIVE_COOLDOWN_SECONDS:
                continue
            if since_bot < MIN_MESSAGES_FOR_PROACTIVE:
                continue
            if random.random() > 0.35:
                continue

            print(f"🧠 Пробую проактивно влезть в чат {chat_id}")
            proactive_text = await generate_proactive_message(chat_id)
            if not proactive_text:
                print("🤐 Не понял тему, молчу")
                continue

            try:
                async with client.action(chat_id, 'typing'):
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    await client.send_message(chat_id, proactive_text)
                print(f"✅ Проактивное сообщение отправлено в {chat_id}: {proactive_text}")
                LAST_BOT_MESSAGE_TIME[chat_id] = time.time()
                MESSAGES_SINCE_BOT[chat_id] = 0
            except Exception as e:
                print(f"Ошибка отправки проактивного сообщения: {e}")

async def main():
    print("🚀 Запуск клиента...")
    await client.start()
    print("✅ Client started")
    print("Авторизован ли пользователь?", await client.is_user_authorized())
    me = await client.get_me()
    print("Это аккаунт:", me.username or me.first_name)
    print("✅ Собир полностью готов к работе!")

    asyncio.create_task(proactive_loop())

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

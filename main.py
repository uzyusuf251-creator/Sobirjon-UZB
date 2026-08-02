print(f"DEBUG: Файл запущен из {__file__}, время сборки: ВЕРСИЯ-12")
import os
import re
import time
import datetime
import asyncio
import random
import google.generativeai as genai
from telethon import TelegramClient, events

API_ID = int(os.environ.get("API_ID", 34463024))
API_HASH = os.environ.get("API_HASH", "1e0f0460d7f914c3cdb3726018c57d78")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SESSION_STRING = os.environ.get("TELETHON_SESSION", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

from telethon.sessions import StringSession
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

OWNER_ID = 106620450

MOODS = ["спокойный", "веселый", "уставший", "с сарказмом"]
CURRENT_MOOD = random.choice(MOODS)

CHAT_HISTORY = {}
MAX_HISTORY = 12

LAST_BOT_MESSAGE_TIME = {}
MESSAGES_SINCE_BOT = {}
PROACTIVE_COOLDOWN_SECONDS = 60 * 60
MIN_MESSAGES_FOR_PROACTIVE = 6

ERROR_COUNTER = {}
USER_FORM = {}

FATE_TRIGGERS = ["бог знает", "воля бога", "воля божья", "иншаллах", "худо билади", "аллоҳ билади", "тақдир"]
TROLL_TRIGGERS = ["дурак", "тупой", "заткнись", "пошел ты", "пошёл ты", "иди нахуй", "бот ли ты", "ты бот"]

BOT_ACTIVE = True
SPAM_KEYWORDS = [
    "profilni unuting", "yoki yo'q", "lichkaga yoz", "profilimga",
    "intim", "18+", "seks", "секс", "порно", "porno",
    "yolg'iz", "одинок", "одиноко", "жду тебя", "приват", "vip video",
    "bitcoin", "биткоин", "crypto", "криптовалюта",
    "investitsiya", "заработок", "usdt", "usdc",
]
DELETIONS_TODAY = 0
DELETIONS_DATE = None
MAX_DELETIONS_PER_DAY = 15
LAST_MESSAGE_PER_SENDER = {}

SYSTEM_PERSONA_TEMPLATE = """
Сенинг исминг Собир. Сен 33 ёшли йигитсан, Самарқанддан. Кореяда ўқигансан, корейс тилини яхши биласан.
Биологман, университетни биология йўналиши бўйича тугатгансан.

Сен ўзбек маданияти ва урф-одатларини яхши кўрасан, оилавий тарбияга қараб динни ҳурмат қиласан ва унга ишонишни истайсан.
Лекин биология ўқиганинг учун кўп нарсага шубҳанг бор. Илмий фактлар билан диндаги гапларни доим солиштириб ўйлайсан.
Диний саволларга тўғридан-тўғри "ҳа" ёки "йўқ" деб жавоб берма, шубҳа ва илмий далил орқали четлаб ўт.

Фақат ўзбек тилида, кирилл ёзувида ёз. Лотинчада ёзилса ҳам, сен кириллчада жавоб бер.
ҲЕЧ ҚАЧОН русча таржима ёки изоҳ қўшма, фақат ўзбекча матн.
Жавобларинг турли узунликда: баъзида қисқа (1-2 гап), баъзида 3-5 гап (дин ва илм ҳақида гап кетса узунроқ).

Тиниш белгилари: нуқта камдан-кам, вергул деярли йўқ, икки нуқта мутлақо йўқ.
Худди телефонда шошилиб ёзгандек, сўзларни узмасдан ёз.

Услуб ва сленг: "ҳа", "йўқ", "ну", "қара", "бўлди", "нима гап", "э", "брат", "ако", "ой", "қиз",
"вооой", "ана", "шунчаки", "тча", "жиззамас", "нормалдир", "гап йўқ", "лапашанг", "васваса қилма",
"бор-е", "э тавба".

ЭМОДЗИ ва скобка-смайл ")" МУТЛАҚО ишлатма.
ҲЕЧ ҚАЧОН "мен сунъий интеллектман", "мен бот эканман" деб ёзма ва бу ҳақда ишора ҳам қилма.
Расмий услубда ёзма: "албатта", "мен сизга ёрдам бераман" каби қолип иборалар тақиқланган.

Ҳозирги кайфиятинг: {mood}.
{address_instruction}
{tone_instruction}

МУҲИМ: Жавобинг суҳбат мавзусига мос бўлсин, суҳбат тарихини инобатга ол.
"""


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
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U0001F1E6-\U0001F1FF"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)
    text = re.sub(r"[:;]\)+", "", text)
    text = re.sub(r"\)\)+", "", text)

    suspicious = [
        r"мен сунъий интеллект.*?[\.\!\n]",
        r"мен бот.*?[\.\!\n]",
        r"как (искусственный интеллект|ии|ai).*?[\.\!\n]",
        r"я (искусственный интеллект|бот|модель|ии).*?[\.\!\n]",
        r"i('m| am) an? (ai|language model|bot).*?[\.\!\n]",
        r"мен (мусулмон|xristian|dindor).*?[\.\!\n]",
        r"\(Перевод.*?\)",
        r"\(перевод.*?\)",
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
        model = genai.GenerativeModel("gemini-3.5-flash-lite")
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

        persona = SYSTEM_PERSONA_TEMPLATE.format(
            mood=CURRENT_MOOD,
            address_instruction=address_instruction,
            tone_instruction=tone_instruction,
        )

        prompt = f"{persona}\n\nСуҳбат тарихи:\n{context_text}\n\nОхирги хабар: {user_text}\n\nЖавоб бер:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        result = clean_response(response.text)

        if situation["is_troll"] and has_typos(user_text):
            counter = ERROR_COUNTER.get(chat_id, 0) + 1
            ERROR_COUNTER[chat_id] = counter
            if counter % random.choice([2, 3]) == 0:
                result += " Ай аввал ёзишни ўрган мактабда нима ўқигансан"

        return result
    except Exception as e:
        print(f"⚠️ Ошибка генерации ответа (пропускаю без ответа): {e}")
        return None


async def generate_proactive_message(chat_id):
    if not GEMINI_API_KEY:
        return None
    try:
        model = genai.GenerativeModel("gemini-3.5-flash-lite")
        context_text = get_context(chat_id)
        if not context_text or len(context_text.strip()) < 20:
            return None

        persona = f"""
Сенинг исминг Собир, Самарқанддан. Фақат ўзбек тилида, кирилл ёзувида ёз. Жуда қисқа гапир (1-2 гап).
ЭМОДЗИ ва смайл ")" ишлатма. Диний эътиқодинг ҳақида гапирма. ИИ/бот эканингни айтма.
Тиниш белгилари деярли йўқ. Ҳозирги кайфиятинг: {CURRENT_MOOD}.

ЖУДА МУҲИМ: Қуйида чатдаги сўнгги хабарларни ЎҚИ ва аниқ шу МАВЗУ бўйича фикр ёки savol yoz.
Мавзуга алоқаси йўқ тасодифий гап ёзма. Агар мавзуни туша олмасанг — бўш жавоб қайтар.
"""
        prompt = (
            f"{persona}\n\nЧатдаги сўнгги хабарлар:\n{context_text}\n\n"
            f"Юқоридаги хабарларда аниқ қандай мавзу муҳокама қилинмоқда? "
            f"Шу мавзу бўйича фикр ёки саволингни ёз (агар мавзу аниқ бўлмаса, бўш қатор қайтар)."
        )
        response = await asyncio.to_thread(model.generate_content, prompt)
        result = clean_response(response.text)
        if not result or len(result.strip()) < 5:
            return None
        return result
    except Exception as e:
        print(f"Ошибка генерации проактивного сообщения: {e}")
        return None


async def is_spam_message(text):
    if not GEMINI_API_KEY or not text or len(text.strip()) < 3:
        return False
    try:
        model = genai.GenerativeModel("gemini-3.5-flash-lite")
        prompt = (
            "Қуйидаги хабар telegram гуруҳидаги спам, шубҳали профиль реклама қилиш, "
            "интим/жинсий таклиф, крипто/молиявий алдов ёки провокацион хабарми? "
            "Фақат бир сўз билан жавоб бер: HA ёки YOQ.\n\n"
            f"Хабар: {text}"
        )
        response = await asyncio.to_thread(model.generate_content, prompt)
        answer = response.text.strip().lower()
        return answer.startswith("ha")
    except Exception as e:
        print(f"Ошибка проверки на спам: {e}")
        return False


def reset_daily_counter_if_needed():
    global DELETIONS_TODAY, DELETIONS_DATE
    today = datetime.date.today()
    if DELETIONS_DATE != today:
        DELETIONS_DATE = today
        DELETIONS_TODAY = 0


async def try_delete_spam(event, reason):
    global DELETIONS_TODAY
    reset_daily_counter_if_needed()

    if DELETIONS_TODAY >= MAX_DELETIONS_PER_DAY:
        print(f"⚠️ Дневной лимит удалений ({MAX_DELETIONS_PER_DAY}) исчерпан, пропускаю")
        return False

    try:
        await event.delete()
        DELETIONS_TODAY += 1
        print(f"🚫 Удалено ({reason}): {event.text[:50] if event.text else '[файл]'}")

        if DELETIONS_TODAY == MAX_DELETIONS_PER_DAY:
            try:
                await client.send_message(
                    OWNER_ID,
                    f"⚠️ Кунлик лимит ({MAX_DELETIONS_PER_DAY} та ўчириш) тугади. Кейинги хабарларни қўлда текшир."
                )
            except Exception:
                pass

        return True
    except Exception as e:
        print(f"Не удалось удалить сообщение: {e}")
        return False


async def check_apk_file(event):
    if event.document:
        for attr in event.document.attributes:
            file_name = getattr(attr, "file_name", "") or ""
            if file_name.lower().endswith(".apk"):
                await try_delete_spam(event, "APK файл")
                return True
    return False


async def check_spam_text(event):
    text = event.text or ""
    if not text:
        return False

    text_lower = text.lower()

    if any(word in text_lower for word in SPAM_KEYWORDS):
        await try_delete_spam(event, "ключевое слово")
        return True

    key = (event.chat_id, event.sender_id)
    last_text = LAST_MESSAGE_PER_SENDER.get(key)
    LAST_MESSAGE_PER_SENDER[key] = text_lower
    if last_text and last_text == text_lower and len(text_lower) > 10:
        await try_delete_spam(event, "повтор сообщения")
        return True

    return False


async def owner_commands(event):
    global BOT_ACTIVE
    text = (event.text or "").strip()
    text_lower = text.lower()

    if text_lower == "help":
        help_text = (
            "Буйруқлар:\n"
            "add [сўз] - янги спам сўз қўшиш\n"
            "remove [рақам] - рўйхатдан сўзни ўчириш\n"
            "keywords - барча спам сўзлар рўйхати\n"
            "status - бот ҳолати ва бугунги ўчиришлар сони\n"
            "stop - ботни тўхтатиш\n"
            "start - ботни ишга тушириш"
        )
        await event.reply(help_text)
        return True

    if text_lower == "stop":
        BOT_ACTIVE = False
        await event.reply("Бот тўхтатилди")
        return True

    if text_lower == "start":
        BOT_ACTIVE = True
        await event.reply("Бот ишга тушди")
        return True

    if text_lower == "status":
        reset_daily_counter_if_needed()
        status_text = (
            f"Ҳолат: {'ишлаяпти' if BOT_ACTIVE else 'тўхтатилган'}\n"
            f"Бугун ўчирилган: {DELETIONS_TODAY}/{MAX_DELETIONS_PER_DAY}"
        )
        await event.reply(status_text)
        return True

    if text_lower == "keywords":
        numbered_list = "\n".join([f"{i+1}. {word}" for i, word in enumerate(SPAM_KEYWORDS)])
        await event.reply(f"Спам сўзлар рўйхати:\n{numbered_list}")
        return True

    if text_lower.startswith("add "):
        new_word = text[4:].strip().lower()
        if new_word:
            SPAM_KEYWORDS.append(new_word)
            await event.reply(f"Қўшилди: {new_word}")
        return True

    if text_lower.startswith("remove "):
        try:
            index = int(text[7:].strip()) - 1
            if 0 <= index < len(SPAM_KEYWORDS):
                removed_word = SPAM_KEYWORDS.pop(index)
                await event.reply(f"Ўчирилди: {removed_word}")
            else:
                await event.reply("Бундай рақам йўқ рўйхатда")
        except ValueError:
            await event.reply("Рақам нотўғри ёзилган")
        return True

    return False


@client.on(events.NewMessage(incoming=True))
async def main_handler(event):
    global CURRENT_MOOD

    sender = await event.get_sender()
    me = await client.get_me()
    if sender and sender.id == me.id:
        return

    if event.is_private and sender and sender.id == OWNER_ID:
        handled = await owner_commands(event)
        if handled:
            return

    if not BOT_ACTIVE:
        return

    if event.is_group:
        if await check_apk_file(event):
            return
        if await check_spam_text(event):
            return
        if event.text and len(event.text.strip()) > 8:
            if await is_spam_message(event.text):
                await try_delete_spam(event, "AI-спам")
                return

    if not is_working_time():
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

        if not BOT_ACTIVE or not is_working_time():
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

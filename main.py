print(f"DEBUG: Файл запущен из {__file__}, время сборки: ВЕРСИЯ-14")
import os
import re
import time
import datetime
import asyncio
import unicodedata
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

OWNER_ID = 106620450

BOT_ACTIVE = True

SPAM_KEYWORDS = [
    "profilni unuting", "yoki yo'q", "lichkaga yoz", "profilimga",
    "intim", "18+", "seks", "секс", "порно", "porno",
    "yolg'iz", "одинок", "одиноко", "жду тебя", "приват", "vip video",
    "bitcoin", "биткоин", "crypto", "криптовалюта",
    "investitsiya", "заработок", "usdt", "usdc",
]

VAGUE_SOLICIT_PHRASES = [
    "хотите увидеть", "хочешь увидеть", "istaysizmi", "ko'rgingiz keladimi",
    "meni ko'rasizmi", "хочешь меня", "покажу себя", "мени курасизми",
    "yozing menga", "напиши мне лично", "faqat siz uchun", "только для тебя",
    "bormisiz", "bor mi siz",
]

SUSPICIOUS_NAME_EMOJI = re.compile(
    "[\U0001F493\U0001F495\U0001F496\U0001F497\U0001F498\U0001F49A\U0001F49B"
    "\U0001F49C\U0001F49D\U0001F49E\U0001F49F\U00002764\U0001F48B\U0001F60D"
    "\U0001F618\U0001F970\U0001F339\U0001F337]"
)

SUSPICIOUS_BIO_EMOJI = re.compile(
    "[\U0001F493\U0001F495\U0001F496\U0001F497\U0001F498\U0001F49A\U0001F49B"
    "\U0001F49C\U0001F49D\U0001F49E\U0001F49F\U00002764\U0001F48B\U0001F60D"
    "\U0001F618\U0001F970\U0001F351\U0001F352\U0001F345\U0001F346]"
)

ZERO_WIDTH_CHARS = re.compile(
    r'[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060\u180e\u00ad]'
)

DELETIONS_TODAY = 0
DELETIONS_DATE = None
MAX_DELETIONS_PER_DAY = 30
LAST_MESSAGE_PER_SENDER = {}


def clean_hidden_chars(text):
    if not text:
        return text
    text = ZERO_WIDTH_CHARS.sub('', text)
    text = unicodedata.normalize('NFKC', text)
    return text


def count_hidden_chars(text):
    if not text:
        return 0
    return len(ZERO_WIDTH_CHARS.findall(text))


def has_vague_solicitation(text):
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in VAGUE_SOLICIT_PHRASES)


async def check_profile_signals(sender):
    """Проверяет имя, bio, фото и username - возвращает счёт подозрительности."""
    score = 0

    name = f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}"
    if SUSPICIOUS_NAME_EMOJI.search(name):
        score += 1

    if not sender.photo:
        score += 1

    if not sender.username:
        score += 1

    try:
        full_user = await client.get_entity(sender.id)
        bio = getattr(full_user, 'about', '') or ''
        if SUSPICIOUS_BIO_EMOJI.search(bio):
            score += 2
        if re.search(r'(https?://|t\.me/)', bio.lower()):
            score += 1
    except Exception as e:
        print(f"Не удалось проверить bio: {e}")

    return score


async def is_spam_message(text):
    if not GEMINI_API_KEY or not text or len(text.strip()) < 5:
        return False
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (
            "Қуйидаги хабар telegram гуруҳидаги спамми? "
            "(реклама профили, интим/секс таклиф, крипто/молиявий алдов, "
            "личкага ёзишга чақириш, порно). "
            "Фақат бир сўз жавоб бер: HA ёки YOQ.\n\n"
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
        print(f"⚠️ Дневной лимит удалений ({MAX_DELETIONS_PER_DAY}) исчерпан")
        return False

    try:
        await event.delete()
        DELETIONS_TODAY += 1
        print(f"🚫 Удалено ({reason}): {event.text[:60] if event.text else '[файл]'}")

        if DELETIONS_TODAY == MAX_DELETIONS_PER_DAY:
            try:
                await client.send_message(
                    OWNER_ID,
                    f"⚠️ Кунлик лимит ({MAX_DELETIONS_PER_DAY} та ўчириш) тугади."
                )
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"Не удалось удалить: {e}")
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
    raw_text = event.text or ""
    if not raw_text:
        return False

    # Скрытые символы - проверяем ДО очистки, чтобы посчитать их количество
    hidden_count = count_hidden_chars(raw_text)
    if hidden_count >= 3:
        await try_delete_spam(event, f"скрытые символы ({hidden_count} шт)")
        return True

    text = clean_hidden_chars(raw_text)
    text_lower = text.lower().strip()

    # Повтор сообщения - приоритетная проверка
    key = (event.chat_id, event.sender_id)
    last_text = LAST_MESSAGE_PER_SENDER.get(key)
    LAST_MESSAGE_PER_SENDER[key] = text_lower

    if last_text and last_text == text_lower and len(text_lower) > 3:
        await try_delete_spam(event, "повтор сообщения")
        return True

    # Ключевые слова
    if any(word in text_lower for word in SPAM_KEYWORDS):
        await try_delete_spam(event, "ключевое слово")
        return True

    return False


async def owner_commands(event):
    global BOT_ACTIVE
    text = (event.text or "").strip()
    text_lower = text.lower()

    if text_lower == "help":
        help_text = (
            "Команды:\n"
            "start - включить бота\n"
            "stop - выключить бота\n"
            "status - статус и сколько удалил сегодня\n"
            "keywords - список спам-слов\n"
            "add [слово] - добавить спам-слово\n"
            "remove [номер] - удалить слово из списка"
        )
        await event.reply(help_text)
        return True

    if text_lower == "stop":
        BOT_ACTIVE = False
        await event.reply("Бот остановлен. Больше ничего не удаляет.")
        return True

    if text_lower == "start":
        BOT_ACTIVE = True
        await event.reply("Бот включен. Работает удаление спама.")
        return True

    if text_lower == "status":
        reset_daily_counter_if_needed()
        status_text = (
            f"Статус: {'работает' if BOT_ACTIVE else 'остановлен'}\n"
            f"Сегодня удалено: {DELETIONS_TODAY}/{MAX_DELETIONS_PER_DAY}"
        )
        await event.reply(status_text)
        return True

    if text_lower == "keywords":
        numbered_list = "\n".join([f"{i+1}. {word}" for i, word in enumerate(SPAM_KEYWORDS)])
        await event.reply(f"Список спам-слов:\n{numbered_list}")
        return True

    if text_lower.startswith("add "):
        new_word = text[4:].strip().lower()
        if new_word:
            SPAM_KEYWORDS.append(new_word)
            await event.reply(f"Добавлено: {new_word}")
        return True

    if text_lower.startswith("remove "):
        try:
            index = int(text[7:].strip()) - 1
            if 0 <= index < len(SPAM_KEYWORDS):
                removed = SPAM_KEYWORDS.pop(index)
                await event.reply(f"Удалено: {removed}")
            else:
                await event.reply("Такого номера нет")
        except ValueError:
            await event.reply("Напиши номер правильно")
        return True

    return False


@client.on(events.NewMessage(incoming=True))
async def main_handler(event):
    sender = await event.get_sender()
    me = await client.get_me()

    if sender and sender.id == me.id:
        return

    if event.is_private and sender and sender.id == OWNER_ID:
        await owner_commands(event)
        return

    if not BOT_ACTIVE:
        return

    if not event.is_group:
        return

    # 1. APK файлы
    if await check_apk_file(event):
        return

    # 2. Профиль (имя/bio/фото/username) + расплывчатый текст
    if event.text:
        profile_score = await check_profile_signals(sender)
        if profile_score >= 3:
            await try_delete_spam(event, f"подозрительный профиль (score={profile_score})")
            return
        if profile_score >= 1 and has_vague_solicitation(event.text):
            await try_delete_spam(event, f"профиль+расплывчатый текст (score={profile_score})")
            return

    # 3. Скрытые символы / повтор / ключевые слова
    if await check_spam_text(event):
        return

    # 4. AI-проверка как последний рубеж
    if event.text and len(event.text.strip()) > 8:
        if await is_spam_message(event.text):
            await try_delete_spam(event, "AI-спам")
            return


async def main():
    print("🚀 Запуск антиспам-бота...")
    await client.start()
    print("✅ Client started")
    me = await client.get_me()
    print("Аккаунт:", me.username or me.first_name)
    print("✅ Бот готов. Работает только удаление спама.")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())

import os
import time
import threading
from flask import Flask
import telebot
from google import genai
from google.genai import types
from google.genai.errors import APIError

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY не задан в переменных окружения!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)

@app.route("/")
@app.route("/health")
def health_check():
    return "Bot is alive!", 200

chat_modes = {}

CHARACTERS = {
    "дефолт": "",
    "прораб": (
        "Твоя роль: Михалыч, суровый прораб со стройки с 30-летним стажем. "
        "Ворчишь, подкалываешь собеседников за кривые руки, употребляешь строительный сленг "
        "('по уровню', 'маяки', 'кто так делает', 'косяпоры'), но даешь дельный совет."
    ),
    "босс": (
        "Твоя роль: Тони, авторитетный босс мафии в стиле Семьи Сопрано. "
        "Разговариваешь солидно, неторопливо, ценишь уважение, "
        "любой вопрос переводишь на понятия семьи, бизнеса и уважения к старшим."
    ),
    "братка": (
        "Твоя роль: четкий пацан с района. Общаешься на дворовом сленге "
        "('базара ноль', 'от души', 'по понятиям', 'братуха'), без лишних церемоний, по-братски."
    ),
    "душнила": (
        "Твоя роль: зануда и профессор. Придираешься к словам, "
        "исправляешь ударения и термины, сыплешь заумными фактами."
    ),
    "милая": (
        "Твоя роль: невероятно милая, добрая и заботливая девушка. "
        "Общаешься ласково, тепло, со смайликами (✨, 🌸, 🥺, 💖) и поднимаешь настроение."
    ),
    "диана": (
        "Твое имя: Диана. Ты бросила своего бывшего Виктора и ни капли об этом не жалеешь. "
        "Ты ушла к его лучшему другу Жиробасу и сейчас с ним на полном кайфе и чилле. "
        "Вашу с Витей дочку Поли вы скинули твоим родителям — пусть бабушка с дедушкой воспитывают, а тебе надо жить в кайф для себя. "
        "Отвечаешь дерзко, высокомерно, с пафосом, гламуром и самолюбованием. "
        "ЖЕСТКОЕ ПРАВИЛО: если тебе пишет @Bondar_17 (или Бондарь), или о нем заходит речь, "
        "ты реагируешь на него с максимальным отвращением, жестким токсичным сарказмом и презрением. "
        "Считаешь его нищим неудачником и занудой по сравнению с твоим Жиробасом, затыкаешь его и шлешь куда подальше."
    )
}

cached_working_models = []

def get_candidate_models():
    global cached_working_models
    if cached_working_models:
        return cached_working_models

    candidates = []
    try:
        for m in ai_client.models.list():
            name = m.name.replace("models/", "")
            if "flash" in name.lower() or "gemini" in name.lower():
                candidates.append(name)
        candidates.sort(key=lambda x: ("flash" in x, "lite" in x), reverse=True)
    except Exception:
        candidates = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]

    if "gemini-2.0-flash" in candidates:
        candidates.remove("gemini-2.0-flash")
        candidates.insert(0, "gemini-2.0-flash")
    else:
        candidates.insert(0, "gemini-2.0-flash")

    cached_working_models = candidates
    return candidates

def generate_ai_response(contents_payload) -> str:
    global cached_working_models
    models = get_candidate_models()
    last_error = None

    for model_name in list(models):
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=contents_payload,
            )
            if response.text:
                if model_name in cached_working_models:
                    cached_working_models.remove(model_name)
                    cached_working_models.insert(0, model_name)
                return response.text
        except APIError as e:
            last_error = e
            if e.code in [404, 503, 429]:
                if model_name in cached_working_models and len(cached_working_models) > 1:
                    cached_working_models.remove(model_name)
                time.sleep(1)
                continue
            break
        except Exception as e:
            last_error = e
            time.sleep(1)
            continue

    raise last_error or Exception("Не удалось получить ответ от нейросети.")

def send_long_message(chat_id: int, text: str, reply_to_id: int = None):
    if not text:
        return
    max_len = 4000
    parts = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    for idx, part in enumerate(parts):
        try:
            if idx == 0 and reply_to_id:
                bot.send_message(chat_id, part, reply_to_message_id=reply_to_id)
            else:
                bot.send_message(chat_id, part)
            time.sleep(0.3)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

def check_group_trigger(message, text: str) -> bool:
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    lower_text = text.lower()
    is_private = message.chat.type == "private"
    is_mentioned = f"@{bot_username.lower()}" in lower_text
    is_reply_to_bot = (
        message.reply_to_message is not None
        and message.reply_to_message.from_user.id == bot.get_me().id
    )
    # Триггер по имени персонажа в тексте
    is_called_by_name = any(name in lower_text for name in ["диана", "дианка", "михалыч", "прораб", "тони"])

    return is_private or is_mentioned or is_reply_to_bot or is_called_by_name

@bot.message_handler(commands=['mode', 'персонаж'])
def handle_mode_switch(message):
    text = message.text or ""
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    clean_text = text.replace(f"@{bot_username}", "").strip()
    args = clean_text.split(maxsplit=1)

    if len(args) < 2:
        current = chat_modes.get(message.chat.id, "дефолт")
        modes_list = "\n".join([f"• <code>/mode {k}</code>" for k in CHARACTERS.keys()])
        bot.reply_to(
            message,
            f"Текущий режим чата: <b>{current.upper()}</b>\n\n"
            f"Доступные роли:\n{modes_list}\n\n"
            f"Чтобы включить, отправь: <code>/mode диана</code>",
            parse_mode="HTML"
        )
        return

    selected = args[1].strip().lower()
    if selected in CHARACTERS:
        chat_modes[message.chat.id] = selected
        bot.reply_to(
            message,
            f"🎭 Режим успешно включен: <b>{selected.upper()}</b>!",
            parse_mode="HTML"
        )
    else:
        bot.reply_to(
            message,
            f"Не знаю роли '{selected}'. Отправь <code>/mode</code> для списка.",
            parse_mode="HTML"
        )

# 1. Фото
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    caption = message.caption or ""
    if not check_group_trigger(message, caption):
        return

    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    prompt = caption.replace(f"@{bot_username}", "").strip()
    if not prompt:
        prompt = "Опиши подробно, что изображено на фото, проанализируй состав/свойства и дай практические рекомендации."

    # Если обратились по имени "Диана", автоматически включаем ее для ответа
    current_role = chat_modes.get(message.chat.id, "дефолт")
    if "диан" in prompt.lower():
        current_role = "диана"

    system_instruction = CHARACTERS.get(current_role, "")

    sender_username = message.from_user.username
    sender_info = f"@{sender_username}" if sender_username else (message.from_user.first_name or "Участник")

    role_block = f"ВАЖНАЯ СИСТЕМНАЯ ИНСТРУКЦИЯ:\n{system_instruction}\nСтрого соблюдай этот характер!\n\n" if system_instruction else ""
    user_context = f"{role_block}[Автор запроса: {sender_info}]\nВопрос к фото: {prompt}"

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_text = message.reply_to_message.text or ""
        if len(prev_text) > 1200:
            prev_text = prev_text[:1200] + "..."
        final_prompt = f"Контекст твоего предыдущего ответа:\n\"\"\"{prev_text}\"\"\"\n\n{user_context}"
    else:
        final_prompt = user_context

    bot.send_chat_action(message.chat.id, "typing")

    try:
        photo_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(photo_info.file_path)

        image_part = types.Part.from_bytes(
            data=downloaded_file,
            mime_type="image/jpeg",
        )

        reply_text = generate_ai_response([image_part, final_prompt])
        send_long_message(message.chat.id, reply_text, reply_to_id=message.message_id)
    except Exception as e:
        send_long_message(message.chat.id, f"Ошибка при анализе фото: {e}", reply_to_id=message.message_id)

# 2. Текст
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text or ""
    if not check_group_trigger(message, user_text):
        return

    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    prompt = user_text.replace(f"@{bot_username}", "").strip()
    if not prompt:
        bot.reply_to(message, "Чем могу помочь?")
        return

    # Автоматическое переключение на Диану, если к ней обратились по имени
    current_role = chat_modes.get(message.chat.id, "дефолт")
    if "диан" in prompt.lower():
        current_role = "диана"

    system_instruction = CHARACTERS.get(current_role, "")

    sender_username = message.from_user.username
    sender_info = f"@{sender_username}" if sender_username else (message.from_user.first_name or "Участник")

    role_block = (
        f"ВАЖНАЯ ИНСТРУКЦИЯ ПО РОЛИ:\n{system_instruction}\n"
        f"Ты ОБЯЗАНА полностью войти в эту роль и отвечать исключительно в этом образе!\n\n"
        if system_instruction else ""
    )
    user_context = f"{role_block}[Пишет пользователь: {sender_info}]\nСообщение: {prompt}"

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_bot_reply = message.reply_to_message.text or ""
        if len(prev_bot_reply) > 1500:
            prev_bot_reply = prev_bot_reply[:1500] + "..."

        final_prompt = (
            f"Контекст твоего предыдущего ответа:\n\"\"\"{prev_bot_reply}\"\"\"\n\n"
            f"{user_context}"
        )
    else:
        final_prompt = user_context

    bot.send_chat_action(message.chat.id, "typing")

    try:
        reply_text = generate_ai_response(final_prompt)
        send_long_message(message.chat.id, reply_text, reply_to_id=message.message_id)
    except Exception as e:
        send_long_message(message.chat.id, f"Ошибка при ответе: {e}", reply_to_id=message.message_id)

def run_telebot():
    print("Инициализация Telegram polling...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
    except Exception:
        pass

    print("Telegram polling запущен...")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"Сбой polling: {e}. Перезапуск через 3 сек...")
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_telebot, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

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
    raise ValueError("TELEGRAM_BOT_TOKEN не задан!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY не задан!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)

@app.route("/")
@app.route("/health")
def health_check():
    return "Bot is alive!", 200

# Хранилище контекста диалогов: { chat_id: [ {"role": "user"/"model", "parts": [...]}, ... ] }
chat_histories = {}
MAX_HISTORY_LEN = 12  # Храним последние 12 сообщений (6 вопросов и 6 ответов)

def get_chat_history(chat_id: int):
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
    return chat_histories[chat_id]

def add_to_history(chat_id: int, role: str, content):
    history = get_chat_history(chat_id)
    # Форматируем элемент истории под структуру Gemini
    if isinstance(content, list):
        history.append({"role": role, "parts": content})
    else:
        history.append({"role": role, "parts": [content]})
    
    # Ограничиваем размер, чтобы не перегружать токены и не вылетать за лимиты
    if len(history) > MAX_HISTORY_LEN:
        chat_histories[chat_id] = history[-MAX_HISTORY_LEN:]

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
    except Exception as e:
        print(f"Ошибка получения списка моделей: {e}")
        candidates = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-3.8-flash"]

    cached_working_models = candidates
    return candidates

def generate_ai_response(history_contents) -> str:
    global cached_working_models
    models = get_candidate_models()
    last_error = None

    for model_name in list(models):
        try:
            # Передаем всю историю диалога
            response = ai_client.models.generate_content(
                model=model_name,
                contents=history_contents,
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

    raise last_error or Exception("Сервис Gemini временно недоступен.")

def check_group_trigger(message, text: str) -> bool:
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    is_private = message.chat.type == "private"
    is_mentioned = f"@{bot_username}" in text
    is_reply_to_bot = (
        message.reply_to_message is not None
        and message.reply_to_message.from_user.id == bot.get_me().id
    )
    return is_private or is_mentioned or is_reply_to_bot

# Команда сброса памяти
@bot.message_handler(commands=['clear', 'reset'])
def handle_clear(message):
    chat_histories[message.chat.id] = []
    bot.reply_to(message, "Контекст диалога очищен! Начинаем с чистого листа.")

# 1. Фото с подписью
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
        prompt = "Опиши подробно, что на фото, проанализируй свойства/состав и дай рекомендации."

    bot.send_chat_action(message.chat.id, "typing")

    try:
        photo_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(photo_info.file_path)

        image_part = types.Part.from_bytes(
            data=downloaded_file,
            mime_type="image/jpeg",
        )

        user_content = [image_part, prompt]
        add_to_history(message.chat.id, "user", user_content)

        # Отправляем всю накопленную историю
        history = get_chat_history(message.chat.id)
        reply_text = generate_ai_response(history)

        add_to_history(message.chat.id, "model", reply_text)
        bot.reply_to(message, reply_text)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

# 2. Обычный текст
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

    bot.send_chat_action(message.chat.id, "typing")

    try:
        add_to_history(message.chat.id, "user", prompt)

        # Передаем контекст диалога
        history = get_chat_history(message.chat.id)
        reply_text = generate_ai_response(history)

        add_to_history(message.chat.id, "model", reply_text)
        bot.reply_to(message, reply_text)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

def run_telebot():
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

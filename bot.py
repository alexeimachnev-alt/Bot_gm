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
        candidates = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite"
        ]

    if "gemini-2.0-flash" in candidates:
        candidates.remove("gemini-2.0-flash")
        candidates.insert(0, "gemini-2.0-flash")
    else:
        candidates.insert(0, "gemini-2.0-flash")

    cached_working_models = candidates
    return candidates

def generate_ai_response(contents_payload) -> str:
    """contents_payload может быть как строкой текста, так и списком [картинка, текст]"""
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
                print(f"Модель {model_name} вернула код {e.code}, переключаемся...")
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
    """Безопасная отправка с нарезкой по 4000 символов"""
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
            print(f"Ошибка отправки сообщения: {e}")

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

# 1. Обработка картинок с подписью
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

    # Если фото прислано в ответ на сообщение бота
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_text = message.reply_to_message.text or ""
        if len(prev_text) > 1200:
            prev_text = prev_text[:1200] + "..."
        prompt = f"Контекст твоего предыдущего ответа:\n\"\"\"{prev_text}\"\"\"\n\nНовый вопрос к фото:\n\"{prompt}\""

    bot.send_chat_action(message.chat.id, "typing")

    try:
        photo_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(photo_info.file_path)

        image_part = types.Part.from_bytes(
            data=downloaded_file,
            mime_type="image/jpeg",
        )

        reply_text = generate_ai_response([image_part, prompt])
        send_long_message(message.chat.id, reply_text, reply_to_id=message.message_id)
    except Exception as e:
        send_long_message(message.chat.id, f"Ошибка при анализе изображения: {e}", reply_to_id=message.message_id)

# 2. Обработка обычного текста с продолжением диалога через Reply
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

    # ВЕДЕНИЕ ДИАЛОГА: если вы отвечаете (Reply) на сообщение бота
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_bot_reply = message.reply_to_message.text or ""
        if len(prev_bot_reply) > 1500:
            prev_bot_reply = prev_bot_reply[:1500] + "..."

        final_prompt = (
            f"Контекст твоего предыдущего ответа:\n\"\"\"{prev_bot_reply}\"\"\"\n\n"
            f"Вопрос пользователя в продолжение диалога:\n\"{prompt}\"\n\n"
            f"Ответь пользователю с учетом контекста выше."
        )
    else:
        final_prompt = prompt

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

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

# Сессии чатов для сохранения контекста
chat_sessions = {}
active_model_name = None

def get_best_available_model():
    """Запрашивает у Google реальный список доступных моделей для вашего ключа"""
    global active_model_name
    if active_model_name:
        return active_model_name

    try:
        models = [m.name.replace("models/", "") for m in ai_client.models.list()]
        print(f"Доступные модели на аккаунте: {models}")
        
        # Приоритет отдаем моделям линейки Flash
        for name in models:
            if "3.8-flash" in name or "3.5-flash" in name or "flash" in name:
                active_model_name = name
                print(f"Выбрана рабочая модель: {active_model_name}")
                return active_model_name
        
        if models:
            active_model_name = models[0]
            return active_model_name
    except Exception as e:
        print(f"Не удалось получить список моделей: {e}")

    # Запасной вариант по умолчанию
    active_model_name = "gemini-3.8-flash"
    return active_model_name

def get_or_create_chat(chat_id: int):
    model = get_best_available_model()
    if chat_id not in chat_sessions:
        chat_sessions[chat_id] = ai_client.chats.create(model=model)
    return chat_sessions[chat_id]

def send_to_gemini(chat_id: int, message_payload) -> str:
    global active_model_name
    for attempt in range(2):
        try:
            chat = get_or_create_chat(chat_id)
            response = chat.send_message(message_payload)
            if response.text:
                return response.text
        except APIError as e:
            print(f"Ошибка API: {e.code} - {e.message}")
            chat_sessions.pop(chat_id, None)
            
            # При 404 сбрасываем кэш модели, чтобы скрипт переопределил доступную
            if e.code == 404:
                active_model_name = None
                time.sleep(1)
                continue
            elif e.code in [503, 429]:
                time.sleep(2)
                continue
            raise e
        except Exception as e:
            chat_sessions.pop(chat_id, None)
            time.sleep(1)
            raise e

    raise Exception("Сервис Gemini временно недоступен. Попробуйте еще раз.")

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

@bot.message_handler(commands=['clear', 'reset'])
def handle_clear(message):
    chat_sessions.pop(message.chat.id, None)
    bot.reply_to(message, "Память диалога очищена. Начинаем с чистого листа!")

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

        reply_text = send_to_gemini(message.chat.id, [image_part, prompt])
        send_long_message(message.chat.id, reply_text, reply_to_id=message.message_id)
    except Exception as e:
        send_long_message(message.chat.id, f"Ошибка: {e}", reply_to_id=message.message_id)

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
        reply_text = send_to_gemini(message.chat.id, prompt)
        send_long_message(message.chat.id, reply_text, reply_to_id=message.message_id)
    except Exception as e:
        send_long_message(message.chat.id, f"Ошибка: {e}", reply_to_id=message.message_id)

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
            print(f"Сбой polling: {e}. Рестарт через 3 сек...")
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_telebot, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

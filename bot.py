import os
import time
import threading
from datetime import datetime
import pytz
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

# Буфер сообщений за день по чатам: { chat_id: ["Имя: текст", ...] }
daily_chat_logs = {}
MAX_DAY_MESSAGES = 400  # лимит сообщений, чтобы не перегружать контекст

def log_message(chat_id: int, user_name: str, text: str):
    if chat_id not in daily_chat_logs:
        daily_chat_logs[chat_id] = []
    # Сохраняем без спама служебными командами
    if text and not text.startswith("/"):
        clean_entry = f"{user_name}: {text.strip()}"
        daily_chat_logs[chat_id].append(clean_entry)
        if len(daily_chat_logs[chat_id]) > MAX_DAY_MESSAGES:
            daily_chat_logs[chat_id].pop(0)

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

# 1. Фото с вопросом/подписью
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    caption = message.caption or ""
    sender_name = message.from_user.first_name or "Участник"
    if caption:
        log_message(message.chat.id, sender_name, f"[Фото с подписью]: {caption}")

    if not check_group_trigger(message, caption):
        return

    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    prompt = caption.replace(f"@{bot_username}", "").strip()
    if not prompt:
        prompt = "Опиши подробно, что изображено на фото, проанализируй состав/свойства и дай практические рекомендации."

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
        send_long_message(message.chat.id, f"Ошибка при анализе фото: {e}", reply_to_id=message.message_id)

# 2. Обычный текст + сбор логов за день
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text or ""
    sender_name = message.from_user.first_name or "Участник"

    # Запоминаем реплику в дневной журнал чата
    log_message(message.chat.id, sender_name, user_text)

    # Реагируем только если обратились к боту
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

    # Подтягиваем контекст при ответе через Reply
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

# 3. Планировщик шутливого анализа чата в 23:59 (МСК)
def daily_summary_scheduler():
    msk_tz = pytz.timezone("Europe/Moscow")
    last_sent_date = None

    print("Планировщик вечернего анализа чата запущен...")
    while True:
        try:
            now = datetime.now(msk_tz)
            today_str = now.strftime("%Y-%m-%d")

            # Срабатывает ровно в 23:59 по Москве
            if now.hour == 23 and now.minute == 59 and last_sent_date != today_str:
                for chat_id, messages in list(daily_chat_logs.items()):
                    # Если за день написали хотя бы 5 сообщений
                    if len(messages) >= 5:
                        chat_history_text = "\n".join(messages)
                        prompt = (
                            "Перед тобой история сообщений друзей в Telegram-чате за сегодня:\n\n"
                            f"{chat_history_text}\n\n"
                            "Сделай короткий, живой и остроумный дайджест дня для этой компании друзей:\n"
                            "1. Главная тема или драма дня (о чем больше всего спорили/общались).\n"
                            "2. 'Душнила дня' или 'Философ дня' (в добром ключе).\n"
                            "3. Лучшая цитата или мысль дня.\n"
                            "4. Итог дня в 1-2 смешных предложениях.\n\n"
                            "Стиль: дружеский, легкий юмор, без цензурного занудства, но без грубости."
                        )
                        try:
                            summary = generate_ai_response(prompt)
                            header = f"🌙 <b>Итоги дня чата ({now.strftime('%d.%m.%Y')}):</b>\n\n"
                            send_long_message(chat_id, header + summary)
                        except Exception as err:
                            print(f"Ошибка генерации итогов для {chat_id}: {err}")
                    
                    # Очищаем историю чата на следующий день
                    daily_chat_logs[chat_id] = []

                last_sent_date = today_str

        except Exception as e:
            print(f"Ошибка в планировщике итогов дня: {e}")

        time.sleep(30)

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
    threading.Thread(target=run_telebot, daemon=True).start()
    threading.Thread(target=daily_summary_scheduler, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

import os
import time
import threading
from flask import Flask
import telebot
from google import genai
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

# Глобальный список проверенных моделей
cached_working_models = []

def get_candidate_models():
    """Динамически запрашивает у Google список доступных моделей для вашего ключа"""
    global cached_working_models
    if cached_working_models:
        return cached_working_models

    candidates = []
    try:
        # Получаем реальный список моделей, поддерживаемых API
        for m in ai_client.models.list():
            name = m.name.replace("models/", "")
            # Ищем актуальные flash и текстовые модели
            if "flash" in name.lower() or "gemini" in name.lower():
                candidates.append(name)
        
        # Сортируем: сначала flash-модели (они быстрее и бесплатны)
        candidates.sort(key=lambda x: ("flash" in x, "lite" in x), reverse=True)
    except Exception as e:
        print(f"Не удалось получить список моделей через API: {e}")
        # Запасной резервный список, если метод listModels недоступен
        candidates = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-3.8-flash"
        ]

    cached_working_models = candidates
    return candidates

def generate_ai_response(prompt: str) -> str:
    global cached_working_models
    models = get_candidate_models()
    last_error = None

    # Пробуем доступные модели по очереди
    for model_name in list(models):
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response.text:
                # Ставим успешно ответившую модель на первое место для ускорения будущих ответов
                if model_name in cached_working_models:
                    cached_working_models.remove(model_name)
                    cached_working_models.insert(0, model_name)
                return response.text
        except APIError as e:
            last_error = e
            # Если модель не найдена (404) или перегружена (503/429) — исключаем и пробуем следующую
            if e.code in [404, 503, 429]:
                print(f"Модель {model_name} вернула код {e.code}, пробуем следующую...")
                if model_name in cached_working_models and len(cached_working_models) > 1:
                    cached_working_models.remove(model_name)
                time.sleep(1)
                continue
            break
        except Exception as e:
            last_error = e
            time.sleep(1)
            continue

    raise last_error or Exception("Не удалось связаться ни с одной доступной моделью.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text or ""
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    is_private = message.chat.type == "private"
    is_mentioned = f"@{bot_username}" in user_text
    is_reply_to_bot = (
        message.reply_to_message is not None
        and message.reply_to_message.from_user.id == bot.get_me().id
    )

    if not (is_private or is_mentioned or is_reply_to_bot):
        return

    prompt = user_text.replace(f"@{bot_username}", "").strip()
    if not prompt:
        bot.reply_to(message, "Чем могу помочь?")
        return

    bot.send_chat_action(message.chat.id, "typing")

    try:
        reply_text = generate_ai_response(prompt)
        bot.reply_to(message, reply_text)
    except Exception as e:
        bot.reply_to(message, f"Нейросеть сейчас недоступна, повторите попытку позже. ({e})")

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
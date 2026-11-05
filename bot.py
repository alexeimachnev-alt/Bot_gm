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

# Список моделей: если основная перегружена (503), бот мгновенно пробует следующую
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-preview",
    "gemini-2.5-pro",
    "gemini-1.5-flash-latest"
]

def generate_ai_response(prompt: str) -> str:
    last_error = None
    for model_name in MODELS_TO_TRY:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response.text:
                return response.text
        except APIError as e:
            last_error = e
            # При перегрузке (503) или нехватке слотов (429) сразу пробуем следующую
            if e.code in [503, 429]:
                continue
            break
        except Exception as e:
            last_error = e
            break

    raise last_error or Exception("Не удалось получить ответ от моделей.")

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
        bot.reply_to(message, f"Сервера временно перегружены, попробуйте через 10 секунд. ({e})")

def run_telebot():
    print("Telegram polling запущен...")
    # Бесконечный рестарт при любых сбоях сети Telegram
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"Ошибка polling: {e}. Перезапуск через 3 сек...")
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_telebot, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
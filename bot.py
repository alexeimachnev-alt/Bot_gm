import os
import threading
from flask import Flask
import telebot
from google import genai

# Чтение ключей из переменных окружения Render
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY не задан в переменных окружения!")

# Инициализация клиентов
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Веб-сервер Flask для поддержания жизни на Render
app = Flask(__name__)

@app.route("/")
@app.route("/health")
def health_check():
    return "Bot is alive!", 200

# Обработка сообщений в Telegram
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text or ""
    bot_username = bot.get_me().username

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
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        reply_text = response.text or "Не удалось сформировать ответ."
        bot.reply_to(message, reply_text)
    except Exception as e:
        bot.reply_to(message, f"Ошибка при обращении к нейросети: {e}")

# Фоновый запуск Telegram Polling
def run_telebot():
    print("Telegram polling запущен...")
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    t = threading.Thread(target=run_telebot, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
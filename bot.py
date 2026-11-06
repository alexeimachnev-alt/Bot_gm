import os
import time
import threading
from flask import Flask
import telebot
from openai import OpenAI

# Чтение ключей из Environment Render
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Читаем ключ xAI (поддерживаем оба названия переменной)
XAI_API_KEY = (os.getenv("XAI_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в Environment!")
if not XAI_API_KEY:
    raise ValueError("XAI_API_KEY не задан в Environment!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Клиент xAI через стандартный интерфейс OpenAI
ai_client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

app = Flask(__name__)

@app.route("/")
@app.route("/health")
def health_check():
    return "Bot is alive!", 200

def get_grok_response(prompt: str) -> str:
    response = ai_client.chat.completions.create(
        model="grok-beta",
        messages=[
            {"role": "system", "content": "Ты дружелюбный и остроумный помощник в Telegram-чате. Отвечай емко, по делу и с хорошим чувством юмора."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content or "Ответ пуст."

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
        bot.reply_to(message, "Слушаю! О чем поболтаем?")
        return

    bot.send_chat_action(message.chat.id, "typing")

    try:
        reply_text = get_grok_response(prompt)
        bot.reply_to(message, reply_text)
    except Exception as e:
        bot.reply_to(message, f"Ошибка Grok API: {e}")

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
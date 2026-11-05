import os
import threading
from flask import Flask

# Веб-сервер для прохождения проверки Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

import requests
import time
import json
import logging
import config
from gemini import GeminiAPI

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

gemini_api = GeminiAPI()

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}/"
        self.bot_info = self.get_me()
        self.bot_username = self.bot_info.get("username", "")
        logger.info(f"Бот @{self.bot_username} успешно запущен для всех чатов")

    def get_me(self):
        response = requests.get(f"{self.api_url}getMe")
        return response.json().get("result", {})
    
    def get_updates(self, offset=None, timeout=30):
        params = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset
        response = requests.get(f"{self.api_url}getUpdates", params=params)
        return response.json().get("result", [])
    
    def send_message(self, chat_id, text, message_thread_id=None):
        params = {"chat_id": chat_id, "text": text}
        if message_thread_id:
            params["message_thread_id"] = message_thread_id
        response = requests.post(f"{self.api_url}sendMessage", params=params)
        return response.json()
    
    def send_chat_action(self, chat_id, action="typing", message_thread_id=None):
        params = {"chat_id": chat_id, "action": action}
        if message_thread_id:
            params["message_thread_id"] = message_thread_id
        response = requests.post(f"{self.api_url}sendChatAction", params=params)
        return response.json()
    
    def process_message(self, message):
        if "text" not in message:
            return
        
        text = message.get("text", "")
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type", "group")
        user_first_name = message.get("from", {}).get("first_name", "Пользователь")
        message_thread_id = message.get("message_thread_id", None)
        
        if text.startswith("/json"):
            json_data = json.dumps(message, indent=2, ensure_ascii=False)
            self.send_message(chat_id, f"```\n{json_data}\n```", message_thread_id)
            return
            
        if text.startswith("/start"):
            self.send_message(
                chat_id, 
                f"Привет! Я бот с Google Gemini AI. Упомяните меня @{self.bot_username} в группе или напишите прямо сюда.", 
                message_thread_id
            )
            return
        elif text.startswith("/help"):
            help_text = f"Упомяните @{self.bot_username} или ответьте на мое сообщение в группе."
            self.send_message(chat_id, help_text, message_thread_id)
            return

        is_private = (chat_type == "private")
        bot_mentioned = f"@{self.bot_username}".lower() in text.lower()
        reply_to_bot = (
            message.get("reply_to_message", {})
            .get("from", {})
            .get("username", "")
            .lower() == self.bot_username.lower()
        )

        if not (is_private or bot_mentioned or reply_to_bot):
            return

        prompt = text.replace(f"@{self.bot_username}", "").replace(f"@{self.bot_username.lower()}", "").strip()
        
        if not prompt and "reply_to_message" in message:
            prompt = message["reply_to_message"].get("text", "")

        if not prompt:
            self.send_message(chat_id, "Пожалуйста, напишите вопрос после упоминания.", message_thread_id)
            return

        self.send_chat_action(chat_id, "typing", message_thread_id)
        time.sleep(0.5)

        logger.info(f"Запрос от {user_first_name} в чате {chat_id}: {prompt}")
        
        try:
            response = gemini_api.generate_response(prompt)
            self.send_message(chat_id, response, message_thread_id)
        except Exception as e:
            logger.error(f"Ошибка при запросе к Gemini: {e}")
            self.send_message(chat_id, "Ошибка нейросети. Попробуйте еще раз.", message_thread_id)

    def run(self):
        logger.info("Запуск бота в режиме long polling...")
        offset = None
        while True:
            try:
                updates = self.get_updates(offset=offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        self.process_message(update["message"])
            except Exception as e:
                logger.error(f"Ошибка при обработке обновлений: {e}")
                time.sleep(3)

bot = TelegramBot(config.TELEGRAM_TOKEN)
bot.run()
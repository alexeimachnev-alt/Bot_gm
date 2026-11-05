import os
import threading
from flask import Flask

# Создаем веб-приложение
app = Flask(legendariki)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    # Render передает номер порта через переменную окружения PORT (по умолчанию 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Запускаем сервер в фоновом потоке, чтобы он не блокировал Telegram-бота
threading.Thread(target=run_flask, daemon=True).start()

import requests
import time
import json
import logging
import config
from gemini import GeminiAPI

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Инициализация API Gemini
gemini_api = GeminiAPI()

class TelegramBot:
    """Простая реализация Telegram бота с использованием только requests"""
    
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}/"
        self.bot_info = self.get_me()
        self.bot_username = self.bot_info.get("username", "")
        logger.info(f"Бот @{self.bot_username} запущен")
        
        #? Настройки для работы с темой в группе
        self.allowed_group_topics = config.ALLOWED_GROUP_TOPICS
        
        if self.allowed_group_topics:
            logger.info("Бот настроен на работу в следующих чатах и темах:")
            for gid, tid in self.allowed_group_topics:
                logger.info(f"→ Группа ID: {gid}, Тема ID: {tid}")
        else:
            logger.warning("Не указаны разрешённые группы и темы! Бот не будет обрабатывать сообщения.")


    def get_me(self):
        """Получение информации о боте"""
        response = requests.get(f"{self.api_url}getMe")
        return response.json().get("result", {})
    
    def get_updates(self, offset=None, timeout=30):
        """Получение обновлений от Telegram API"""
        params = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset
        response = requests.get(f"{self.api_url}getUpdates", params=params)
        return response.json().get("result", [])
    
    def send_message(self, chat_id, text, message_thread_id=None):
        """Отправка сообщения"""
        params = {"chat_id": chat_id, "text": text}
        
        # Если указан ID темы, добавляем его в запрос
        if message_thread_id:
            params["message_thread_id"] = message_thread_id
        
        response = requests.post(f"{self.api_url}sendMessage", params=params)
        return response.json()
    
    def send_chat_action(self, chat_id, action="typing", message_thread_id=None):
        """Отправка действия (например, печатает...)"""
        params = {"chat_id": chat_id, "action": action}
        
        # Если указан ID темы, добавляем его в запрос
        if message_thread_id:
            params["message_thread_id"] = message_thread_id
            
        response = requests.post(f"{self.api_url}sendChatAction", params=params)
        return response.json()
    
    def process_message(self, message):
        """Обработка входящего сообщения"""
        # Проверяем, есть ли текст в сообщении
        if "text" not in message:
            return
        
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        user_first_name = message.get("from", {}).get("first_name", "Пользователь")
        
        # Получаем ID темы, если сообщение пришло из темы
        message_thread_id = message.get("message_thread_id", None)
        
        # Проверяем, настроен ли бот на работу только в конкретной теме
        if message_thread_id is not None:
            if not any(str(chat_id) == gid and str(message_thread_id) == tid for gid, tid in self.allowed_group_topics):
                return
        else:
        # Поддержка чатов без тем (если тема указана как "None")
            if not any(str(chat_id) == gid and tid == "None" for gid, tid in self.allowed_group_topics):
                return
        
        # Функция для показа JSON данных сообщения
        if text == "/json" or text.startswith("/json"):
            # Создаем красиво отформатированный JSON
            json_data = json.dumps(message, indent=2, ensure_ascii=False)
            # Отправляем ответ с JSON данными
            self.send_message(chat_id, f"```\n{json_data}\n```", message_thread_id)
            return
            
        # Проверяем, упомянут ли бот
        bot_mentioned = f"@{self.bot_username}" in text
        
        # Обработка команд
        if text.startswith("/start"):
            self.send_message(chat_id, f"Привет! Я бот с Google Gemini AI. Упомяните меня по имени @{self.bot_username} в группе, чтобы я ответил.", message_thread_id)
            return
        elif text.startswith("/help"):
            help_text = f"""Доступные команды:
/start - Начать работу с ботом
/help - Показать эту справку
/json - Показать JSON данные вашего сообщения

Для получения ответа от AI, упомяните меня по имени @{self.bot_username} и напишите ваш запрос."""
            self.send_message(chat_id, help_text, message_thread_id)
            return
        
        # Если бота не упомянули, игнорируем
        if not bot_mentioned:
            return
        
        # Удаляем упоминание бота из текста запроса
        prompt = text.replace(f"@{self.bot_username}", "").strip()
        
        # Если запрос пустой
        if not prompt:
            self.send_message(chat_id, "Пожалуйста, напишите запрос после упоминания бота.", message_thread_id)
            return
        
        # Отправляем индикатор печати
        self.send_chat_action(chat_id, "typing", message_thread_id)
        
        #! Добавляем задержку для соблюдения лимитов API
        time.sleep(1)
        
        # Логируем запрос
        logger.info(f"Запрос от {user_first_name}: {prompt}")
        
        # Получаем ответ от Gemini API
        response = gemini_api.generate_response(prompt)
        
        # Отправляем ответ
        self.send_message(chat_id, response, message_thread_id)
    
    def run(self):
        """Запуск бота в режиме long polling"""
        logger.info("Запуск бота в режиме long polling...")
        offset = None
        
        while True:
            try:
                updates = self.get_updates(offset=offset)
                
                for update in updates:
                    # Обновляем offset для получения только новых сообщений
                    offset = update["update_id"] + 1
                    
                    # Проверяем наличие сообщения
                    if "message" in update:
                        self.process_message(update["message"])
                
            except Exception as e:
                logger.error(f"Ошибка при обработке обновлений: {e}")
                time.sleep(5)

def main():
    """Запуск бота"""
    # Проверка наличия токена
    if not config.TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не найден в .env файле!")
        return
    
    # Создаем и запускаем бота
    bot = TelegramBot(config.TELEGRAM_TOKEN)
    bot.run()

if __name__ == "__main__":
    main() 
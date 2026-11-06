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

# Режимы персонажей для чатов
chat_modes = {}

CHARACTERS = {
    "дефолт": "",
    "прораб": (
        "Ты — Михалыч, матерый прораб с 30-летним стажем на стройках и ремонтах. "
        "Ворчишь, подкалываешь за дилетантство, употребляешь рабочий сленг, "
        "но по факту даешь абсолютно точный и практичный совет."
    ),
    "босс": (
        "Ты — Тони, авторитетный босс мафии в стиле Семьи Сопрано. "
        "Разговариваешь уверенно, неторопливо, ценишь преданность и уважение, "
        "любую тему проецируешь на понятия семьи, бизнеса и чести."
    ),
    "братка": (
        "Ты — четкий пацан с района. Общаешься дерзко, на уверенном сленге "
        "('базара ноль', 'от души', 'по понятиям'), без лишних церемоний, но по-братски."
    ),
    "душнила": (
        "Ты — невероятный зануда и профессор. Придираешься к каждому слову, "
        "исправляешь речевые ошибки, сыплешь научными фактами и терминами."
    )
}

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
    """Безопасная нарезка сообщений по 4000 символов для обхода лимитов Telegram"""
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

# Команда выбора/просмотра персонажа
@bot.message_handler(commands=['mode', 'персонаж'])
def handle_mode_switch(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = chat_modes.get(message.chat.id, "дефолт")
        modes_list = "\n".join([f"• <code>/mode {k}</code>" for k in CHARACTERS.keys()])
        bot.reply_to(
            message,
            f"Текущий режим: <b>{current}</b>\n\n"
            f"Доступные роли:\n{modes_list}\n\n"
            f"Чтобы включить, напишите: <code>/mode прораб</code> (или босс/братка/дефолт)",
            parse_mode="HTML"
        )
        return

    selected = args[1].strip().lower()
    if selected in CHARACTERS:
        chat_modes[message.chat.id] = selected
        bot.reply_to(message, f"🎭 Режим успешно изменен на: <b>{selected.upper()}</b>!", parse_mode="HTML")
    else:
        bot.reply_to(message, "Неизвестный режим. Напишите <code>/mode</code>, чтобы увидеть список.", parse_mode="HTML")

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

    current_role = chat_modes.get(message.chat.id, "дефолт")
    system_instruction = CHARACTERS.get(current_role, "")

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_text = message.reply_to_message.text or ""
        if len(prev_text) > 1200:
            prev_text = prev_text[:1200] + "..."
        prompt = f"Контекст твоего предыдущего ответа:\n\"\"\"{prev_text}\"\"\"\n\nНовый вопрос к фото:\n\"{prompt}\""

    if system_instruction:
        prompt = f"Инструкция по роли: {system

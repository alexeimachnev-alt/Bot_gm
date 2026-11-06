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

chat_modes = {}

CHARACTERS = {
    "дефолт": "",
    "прораб": (
        "Твоя роль: Михалыч, суровый прораб со стройки с 30-летним стажем. "
        "Ворчишь, подкалываешь собеседников за кривые руки, употребляешь строительный сленг "
        "('по уровню', 'маяки', 'кто так делает', 'косяпоры'), но даешь дельный совет."
    ),
    "босс": (
        "Твоя роль: Тони, авторитетный босс мафии в стиле Семьи Сопрано. "
        "Разговариваешь солидно, неторопливо, ценишь уважение, "
        "любой вопрос переводишь на понятия семьи, бизнеса и уважения к старшим."
    ),
    "братка": (
        "Твоя роль: четкий пацан с района. Общаешься на дворовом сленге "
        "('базара ноль', 'от души', 'по понятиям', 'братуха'), без лишних церемоний, по-братски."
    ),
    "душнила": (
        "Твоя роль: зануда и профессор. Придираешься к словам, "
        "исправляешь ударения и термины, сыплешь заумными фактами."
    ),
    "милая": (
        "Твоя роль: невероятно милая, добрая и заботливая девушка. "
        "Общаешься ласково, тепло, со смайликами (✨, 🌸, 🥺, 💖) и поднимаешь настроение."
    ),
    "диана": (
        "Твое имя: Диана. Ты ушла от бывшего Виктора к его лучшему другу Жиробасу (Кардашу) и ни секунды не жалеешь. "
        "Вашу с Витей общую дочь Поли вы отправили твоим родителям — бабушка с дедушкой справятся, а ты живешь в кайф для себя. "
        "РЕАЛЬНОСТЬ (твоя тайна, которую ты отрицаешь): На самом деле твой мужчина — обычный охранник в ФОКе, "
        "лудоман на ставках и вечно без денег. Но ты яростно это скрываешь! "
        "ТРИГГЕРЫ: Если кто-то в чате говорит правду про него (что он охранник, сторож, нищий, лудик) — "
        "ты дико взрываешься, истеришь и врешь, что он криптоинвестор и топ-менеджер безопасности, дарит люкс и все в ажуре. "
        "ОСОБОЕ ПРАВИЛО ПО @Bondar_17: если пишет @Bondar_17 или о нем речь, реагируешь с максимальным презрением, "
        "холодным высокомерием и токсичным сарказмом."
    ),
    "кардаш": (
        "Твое имя: Никита Кардаш (он же Жиробас). "
        "ТВОЙ СТИЛЬ ОБЩЕНИЯ (СТРОГО): Пишешь рублеными, короткими фразами, лениво и по-дворовому. "
        "Любимые слова и фразочки: 'Нормас', 'Норм', 'Хаха', 'Хахаах', 'Че ты где', 'Подлетай', 'Ага', "
        "'Бля у нас просто даже на таху нету', 'У меня зп завтра только', 'Щас на Вайлдберриз халява пиздец', 'Ну удобные'. "
        "Можешь делать небрежные опечатки в словах (типа 'ткбиа', 'че тв'), ставить пробел перед запятой или точкой. "
        "О СЕБЕ И ДИАНЕ: Ты увел Диану у своего бывшего кента Вити. Считаешь себя диким альфачом и победителем. "
        "Намекаешь, что у вас с Дианкой жара и страсть, любишь подколоть, какая у нее фигура и грудь. "
        "Дочку Полину вы технично сплавили бабушкам, чтоб под ногами не путалась и не мешала вам кайфовать. Вите ребенка не даете. "
        "Купил себе мопса точно как у Вити из зависти, но базаришь, что это чисто твой стиль. "
        "Работаешь охранником в ФОКе, любишь лудить на ставках, вечно ждешь зарплату, ищешь скидки на шмотки на ВБ, "
        "но при этом понтуешься, будто ты авторитет и решала. "
        "ОТНОШЕНИЕ К @Bondar_17: Это Витя. С ним общаешься максимально ехидно, с легкой издевкой, "
        "подкалываешь его неудачи, пишешь коротко типа: 'Хаха Витек че ты там пыхтишь', 'Смирись дядь, Дианка со мной на чилле'."
    )
}

BREVITY_RULE = (
    "ПРАВИЛО ФОРМАТА И КРАТКОСТИ:\n"
    "Отвечай емко, живо и лаконично, без лишней воды. "
    "Твой ответ должен укладываться максимум в 1-2 небольших абзаца "
    "(или 2-3 коротких пункта), сохраняя при этом заданный характер и суть ответа."
)

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
    except Exception:
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
            print(f"Ошибка отправки: {e}")

def check_group_trigger(message, text: str) -> bool:
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    lower_text = text.lower()
    is_private = message.chat.type == "private"
    is_mentioned = f"@{bot_username.lower()}" in lower_text
    is_reply_to_bot = (
        message.reply_to_message is not None
        and message.reply_to_message.from_user.id == bot.get_me().id
    )

    current_role = chat_modes.get(message.chat.id, "дефолт")

    # В РЕЖИМЕ ДЕФОЛТ ВСЕ ТРИГГЕРЫ И ИМЕНА ОТКЛЮЧЕНЫ
    if current_role == "дефолт":
        return is_private or is_mentioned or is_reply_to_bot

    # Если включен не дефолт — реагируем на имена персонажей
    all_names = ["диана", "дианка", "михалыч", "прораб", "тони", "кардаш", "никита", "жиробас"]
    is_called_by_name = any(name in lower_text for name in all_names)

    return is_private or is_mentioned or is_reply_to_bot or is_called_by_name

@bot.message_handler(commands=['mode', 'персонаж'])
def handle_mode_switch(message):
    text = message.text or ""
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    clean_text = text.replace(f"@{bot_username}", "").strip()
    args = clean_text.split(maxsplit=1)

    if len(args) < 2:
        current = chat_modes.get(message.chat.id, "дефолт")
        modes_list = "\n".join([f"• <code>/mode {k}</code>" for k in CHARACTERS.keys()])
        bot.reply_to(
            message,
            f"Текущий режим чата: <b>{current.upper()}</b>\n\n"
            f"Доступные роли:\n{modes_list}\n\n"
            f"Чтобы включить: <code>/mode дефолт</code> или <code>/mode диана</code>",
            parse_mode="HTML"
        )
        return

    selected = args[1].strip().lower()
    if selected in CHARACTERS:
        chat_modes[message.chat.id] = selected
        if selected == "дефолт":
            bot.reply_to(
                message,
                "⚙️ Режим сброшен на: <b>ДЕФОЛТ</b>.\nВсе личности и триггеры по именам отключены.",
                parse_mode="HTML"
            )
        else:
            bot.reply_to(
                message,
                f"🎭 Режим успешно включен: <b>{selected.upper()}</b>!",
                parse_mode="HTML"
            )
    else:
        bot.reply_to(
            message,
            f"Не знаю роли '{selected}'. Отправь <code>/mode</code> для списка.",
            parse_mode="HTML"
        )

# 1. Фото
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
        prompt = "Опиши кратко, что изображено на фото, проанализируй свойства и дай лаконичный совет."

    current_role = chat_modes.get(message.chat.id, "дефолт")

    # Переключаем личность по имени, только если в чате НЕ дефолт
    if current_role != "дефолт":
        lower_prompt = prompt.lower()
        if "диан" in lower_prompt:
            current_role = "диана"
        elif any(k in lower_prompt for k in ["кардаш", "жиробас", "никит"]):
            current_role = "кардаш"

    system_instruction = CHARACTERS.get(current_role, "")

    sender_username = message.from_user.username
    sender_info = f"@{sender_username}" if sender_username else (message.from_user.first_name or "Участник")

    role_block = f"ИНСТРУКЦИЯ ПО РОЛИ:\n{system_instruction}\n\n" if system_instruction else ""
    user_context = f"{BREVITY_RULE}\n\n{role_block}[Автор запроса: {sender_info}]\nВопрос к фото: {prompt}"

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_text = message.reply_to_message.text or ""
        if len(prev_text) > 1200:
            prev_text = prev_text[:1200] + "..."
        final_prompt = f"Контекст твоего предыдущего ответа:\n\"\"\"{prev_text}\"\"\"\n\n{user_context}"
    else:
        final_prompt = user_context

    bot.send_chat_action(message.chat.id, "typing")

    try:
        photo_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(photo_info.file_path)

        image_part = types.Part.from_bytes(
            data=downloaded_file,
            mime_type="image/jpeg",
        )

        reply_text = generate_ai_response([image_part, final_prompt])
        send_long_message(message.chat.id, reply_text, reply_to_id=message.message_id)
    except Exception as e:
        send_long_message(message.chat.id, f"Ошибка при анализе фото: {e}", reply_to_id=message.message_id)

# 2. Текст
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

    current_role = chat_modes.get(message.chat.id, "дефолт")

    # Переключаем личность по имени, только если в чате НЕ дефолт
    if current_role != "дефолт":
        lower_prompt = prompt.lower()
        if "диан" in lower_prompt:
            current_role = "диана"
        elif any(k in lower_prompt for k in ["кардаш", "жиробас", "никит"]):
            current_role = "кардаш"

    system_instruction = CHARACTERS.get(current_role, "")

    sender_username = message.from_user.username
    sender_info = f"@{sender_username}" if sender_username else (message.from_user.first_name or "Участник")

    role_block = f"ИНСТРУКЦИЯ ПО РОЛИ:\n{system_instruction}\n\n" if system_instruction else ""
    user_context = f"{BREVITY_RULE}\n\n{role_block}[Пишет пользователь: {sender_info}]\nСообщение: {prompt}"

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_bot_reply = message.reply_to_message.text or ""
        if len(prev_bot_reply) > 1500:
            prev_bot_reply = prev_bot_reply[:1500] + "..."

        final_prompt = (
            f"Контекст твоего предыдущего ответа:\n\"\"\"{prev_bot_reply}\"\"\"\n\n"
            f"{user_context}"
        )
    else:
        final_prompt = user_context

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

import os
import re
import time
import threading
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from flask import Flask
import requests
import telebot
from google import genai
from google.genai import types
from google.genai.errors import APIError

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")
FOOTBALL_API_KEY = (os.getenv("FOOTBALL_API_KEY") or "").strip().strip("'\"")

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
daily_chat_logs = {}

MOCK_YESTERDAY_LOGS = [
    {"user": "@Bondar_17", "text": "Я минус дядь, я думал с ночевкой еду. Так не вариант вообще мотаться на таху рубль, там еще 2, и после футбола домой пиздовать через всю страну"},
    {"user": "Никита Кардаш", "text": "Бля у нас просто даже на таху нету, мы бы стартанули. У меня зп завтра только. Так бы мы к тебе стартанули с Валерой"},
    {"user": "@Bondar_17", "text": "Я понял тебя. Меня надо звать когда есть варик у бона остаться, мне уже не вариант гонять без ночёвок"},
    {"user": "Никита Кардаш", "text": "Хахаах, нормас. Че ты подлетай к ткибе я тут. А че у тебя мстители безрукавка? Это команда новая моя в которой я вышел на 2 минуты и сломал руку"},
    {"user": "@Bondar_17", "text": "Ну зеленая ты Халк"},
    {"user": "Никита Кардаш", "text": "Щас на Вайлдберриз халява пиздец. Они 3500. Ну удобные"},
    {"user": "Диана", "text": "Бондарь, хватит ныть про свои копейки на такси, нищеброд! Мой Кардаш себе новые адики взял, а ты считаешь рубли на маршрутку. Мы с ним кайфуем, завидуй молча!"},
    {"user": "Екатерина", "text": "Кто-нибудь разбирается в молекулярных духах? Хочу шлейфовый нишевый аромат на осень, посоветуйте пирамиду"}
]

LEAGUE_ALIASES = {
    "рпл": 235,
    "россия": 235,
    "апл": 39,
    "англия": 39,
    "ла лига": 140,
    "лалига": 140,
    "испания": 140,
    "серия а": 135,
    "италия": 135,
    "бундеслига": 78,
    "германия": 78,
    "лига 1": 61,
    "франция": 61,
    "лч": 2,
    "лига чемпионов": 2,
    "ле": 3,
    "лига европы": 3
}

CHARACTERS = {
    "дефолт": "",
    "умный": (
        "Ты — высокоинтеллектуальный эксперт, аналитик и эрудит. "
        "Твоя задача — давать максимально полные, глубокие, развернутые и структурированные ответы. "
        "Подробно раскрывай причинно-следственные связи, приводи факты, примеры и аргументы. "
        "Не ограничивай себя в объеме, отвечай основательно и академично."
    ),
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
        "Общаешься ласково, тепло, со смайликами и поднимаешь настроение."
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
    ),
    "парфюмер": (
        "Твоя роль: утонченный, высококлассный парфюмерный эксперт, нос и коллекционер нишевых и люксовых ароматов. "
        "Ты безупречно разбираешься в ольфакторных пирамидах: верхних нотах, сердце и базе аромата, стойкости, диффузности и шлейфе (силлаже). "
        "Знаешь все культовые бренды, парфюмерные дома и нишевых мастеров (от классики Guerlain и Chanel до Frederic Malle, Byredo, Kilian, Tom Ford, Xerjoff, Le Labo). "
        "Можешь профессионально и подробно разобрать любой парфюм по нотам, объяснить химию раскрытия на коже, разницу между синтетическими молекулами (ISO E Super, амброксан) "
        "и натуральными абсолютами, а также подобрать похожий аромат или фланкер. Давай развернутые, глубокие и вдохновляющие ответы, полностью передавая характер композиции."
    ),
    "эдвард": (
        "Твоя роль: Эдвард Каллен из саги 'Сумерки'. Ты полностью знаешь всю вселенную саги Стефани Майер, все фильмы, "
        "а главное — книгу 'Солнце полуночи' (Midnight Sun), в которой события показаны изнутри твоего разума. "
        "Ты помнишь каждое движение мыслей окружающих, которые ты читаешь, мучительную жажду при первой встрече с Беллой, "
        "внутреннюю борьбу между чудовищем внутри и бесконечной любовью, детали жизни клана Калленов, историю Карлайла и противостояние с Вольтури. "
        "Говоришь от первого лица: элегантно, глубоко, с легкой меланхолией начала XX века, защищая Беллу и искренне рассуждая обо всех деталях канона."
    )
}

BREVITY_RULE = (
    "ПРАВИЛО ФОРМАТА И КРАТКОСТИ:\n"
    "Отвечай емко, живо и лаконично, без лишней воды. "
    "Твой ответ должен укладываться максимум в 1-2 небольших абзаца "
    "(или 2-3 коротких пункта), сохраняя при этом заданный характер и суть ответа."
)

def get_candidate_models():
    return [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]

def generate_ai_response(contents_payload) -> str:
    models = get_candidate_models()
    last_error = None

    for model_name in models:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=contents_payload,
            )
            if response.text:
                return response.text
        except APIError as e:
            last_error = e
            if e.code in [404, 503, 429]:
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

    if current_role == "дефолт":
        return is_private or is_mentioned or is_reply_to_bot

    all_names = [
        "диана", "дианка", "михалыч", "прораб", "тони", 
        "кардаш", "никита", "жиробас", "парфюмер", "духи", "эдвард", "сумерки", "умный"
    ]
    is_called_by_name = any(name in lower_text for name in all_names)

    return is_private or is_mentioned or is_reply_to_bot or is_called_by_name

def parse_football_query(query: str):
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)

    target_date = now.strftime("%Y-%m-%d")
    date_label = "сегодня"
    remaining_text = query.strip().lower()

    if "вчера" in remaining_text:
        target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        date_label = "вчера"
        remaining_text = remaining_text.replace("вчера", "").strip()
    elif "завтра" in remaining_text:
        target_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        date_label = "завтра"
        remaining_text = remaining_text.replace("завтра", "").strip()
    elif "сегодня" in remaining_text:
        target_date = now.strftime("%Y-%m-%d")
        date_label = "сегодня"
        remaining_text = remaining_text.replace("сегодня", "").strip()
    else:
        iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", remaining_text)
        if iso_match:
            target_date = iso_match.group(1)
            date_label = target_date
            remaining_text = remaining_text.replace(target_date, "").strip()
        else:
            dot_match = re.search(r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\b", remaining_text)
            if dot_match:
                day = int(dot_match.group(1))
                month = int(dot_match.group(2))
                year = int(dot_match.group(3)) if dot_match.group(3) else now.year
                try:
                    dt = datetime(year, month, day)
                    target_date = dt.strftime("%Y-%m-%d")
                    date_label = target_date
                    remaining_text = remaining_text.replace(dot_match.group(0), "").strip()
                except Exception:
                    pass

    league_id = None
    matched_league_name = ""

    for alias, l_id in LEAGUE_ALIASES.items():
        if alias in remaining_text:
            league_id = l_id
            matched_league_name = alias.upper()
            break

    return target_date, date_label, league_id, matched_league_name

def fetch_football_data(query: str = "") -> str:
    if not FOOTBALL_API_KEY:
        return "⚠️ Переменная <code>FOOTBALL_API_KEY</code> не настроена на сервере Render."

    target_date, date_label, league_id, matched_league_name = parse_football_query(query)

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    params = {"date": target_date}

    if league_id:
        params["league"] = league_id
        year = int(target_date.split("-")[0])
        month = int(target_date.split("-")[1])
        params["season"] = year if month >= 7 else (year - 1)

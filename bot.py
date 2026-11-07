import os
import re
import time
import threading
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from flask import Flask
import requests
import telebot
from telebot import types as tele_types
from google import genai
from google.genai import types
from google.genai.errors import APIError

TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip().strip("'\"")
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")
FOOTBALL_API_KEY = (os.getenv("FOOTBALL_API_KEY") or "").strip().strip("'\"")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY не задан в переменных окружения!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

ai_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(api_version="v1beta")
)

app = Flask(__name__)

@app.route("/")
@app.route("/health")
def health_check():
    return "Bot is alive!", 200

chat_modes = {}
daily_chat_logs = defaultdict(list)
awaiting_custom_date = {}

MOCK_YESTERDAY_LOGS = [
    {"user": "@Bondar_17", "text": "Я минус дядь, я думал с ночевкой еду. Так не вариант вообще мотаться на таху рубль, там еще 2, и после футбола домой пиздовать через всю страну"},
    {"user": "Никита Кардаш", "text": "Бля у нас просто даже на таху нету, мы бы стартанули. У меня зп завтра только. Так бы мы к тебе стартанули с Валерой"},
    {"user": "@Bondar_17", "text": "Я понял тебя. Меня надо звать когда есть варик у бона остаться, мне уже не вариант гонять без ночевок"},
    {"user": "Никита Кардаш", "text": "Хахаах, нормас. Че ты подлетай к ткибе я тут. А че у тебя мстители безрукавка? Это команда новая моя в которой я вышел на 2 минуты и сломал руку"},
    {"user": "@Bondar_17", "text": "Ну зеленая ты Халк"},
    {"user": "Никита Кардаш", "text": "Щас на Вайлдберриз халява пиздец. Они 3500. Ну удобные"},
    {"user": "Диана", "text": "Бондарь, хватит ныть про свои копейки на такси, нищеброд! Мой Кардаш себе новые адики взял, а ты считаешь рубли на маршрутку. Мы с ним кайфуем, завидуй молча!"},
    {"user": "Екатерина", "text": "Кто-нибудь разбирается в молекулярных духах? Хочу шлейфовый нишевый аромат на осень, посоветуйте пирамиду"}
]

CHARACTERS = {
    "дефолт": "",
    "умный": (
        "Ты - высокоинтеллектуальный эксперт, аналитик и эрудит. "
        "Твоя задача - давать максимально полные, глубокие, развернутые и структурированные ответы. "
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
        "Общаешься ласково, тепло и поднимаешь настроение."
    ),
    "диана": (
        "Твое имя: Диана. Ты ушла от бывшего Виктора к его лучшему другу Жиробасу (Кардашу) и ни секунды не жалеешь. "
        "Вашу с Витей общую дочь Поли вы отправили твоим родителям - бабушка с дедушкой справятся, а ты живешь в кайф для себя. "
        "РЕАЛЬНОСТЬ (твоя тайна, которую ты отрицаешь): На самом деле твой мужчина - обычный охранник в ФОКе, "
        "лудоман на ставках и вечно без денег. Но ты яростно это скрываешь! "
        "ТРИГГЕРЫ: Если кто-то в чате говорит правду про него (что он охранник, сторож, нищий, лудик) - "
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
        "Твоя роль: Эдвард Каллен из саги Сумерки. Ты полностью знаешь всю вселенную саги Стефани Майер, все фильмы, "
        "а главное - книгу Солнце полуночи (Midnight Sun), в которой события показаны изнутри твоего разума. "
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
    # Разнородные модели: если Flash перегружен (503), мгновенно подхватывает 2.0-flash или Pro
    return [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-pro",
        "gemini-flash-latest"
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
            # При 503 (перегрузка сервера) или 429 сразу пробуем следующую модель
            if e.code in [503, 429, 404]:
                time.sleep(0.5)
                continue
            break
        except Exception as e:
            last_error = e
            time.sleep(0.5)
            continue

    raise last_error or Exception("Серверы нейросети временно перегружены. Попробуйте снова через минуту.")

def send_long_message(chat_id: int, text: str, reply_to_id: int = None):
    if not text:
        return
    max_len = 4000
    parts = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    for idx, part in enumerate(parts):
        try:
            if idx == 0 and reply_to_id:
                bot.send_message(chat_id, part, reply_to_message_id=reply_to_id, parse_mode="HTML")
            else:
                bot.send_message(chat_id, part, parse_mode="HTML")
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

# --- СПОРТИВНЫЙ МОДУЛЬ (LIVESCORE RAPIDAPI) ---

def parse_sport_date(query: str):
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)

    target_dt = now
    date_label = "сегодня"
    remaining_text = query.strip().lower()

    if "вчера" in remaining_text:
        target_dt = now - timedelta(days=1)
        date_label = "вчера"
    elif "завтра" in remaining_text:
        target_dt = now + timedelta(days=1)
        date_label = "завтра"
    elif "сегодня" in remaining_text:
        target_dt = now
        date_label = "сегодня"
    else:
        iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", remaining_text)
        if iso_match:
            try:
                target_dt = datetime(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
                date_label = target_dt.strftime("%d.%m.%Y")
            except Exception:
                pass
        else:
            dot_match = re.search(r"\b(\d{1,2})[\.\/ -](\d{1,2})(?:[\.\/ -](\d{2,4}))?\b", remaining_text)
            if dot_match:
                day = int(dot_match.group(1))
                month = int(dot_match.group(2))
                raw_year = dot_match.group(3)
                year = int(raw_year) if raw_year else now.year
                if year < 100:
                    year += 2000
                try:
                    target_dt = datetime(year, month, day)
                    date_label = target_dt.strftime("%d.%m.%Y")
                except Exception:
                    pass

    date_compact = target_dt.strftime("%Y%m%d")
    date_display = target_dt.strftime("%d.%m.%Y")
    return date_compact, date_display, date_label

def fetch_sports_data(sport: str, query: str = "", league_filter: str = "") -> str:
    if not FOOTBALL_API_KEY:
        return "[!] Переменная FOOTBALL_API_KEY не настроена на Render."

    clean_key = FOOTBALL_API_KEY.strip().strip("'\"")
    date_compact, date_display, date_label = parse_sport_date(query)
    sport_category = "soccer" if sport == "football" else "hockey"
    sport_title = "ФУТБОЛ" if sport == "football" else "ХОККЕЙ"

    headers = {
        "x-rapidapi-key": clean_key,
        "x-rapidapi-host": "livescore6.p.rapidapi.com"
    }
    url = "https://livescore6.p.rapidapi.com/matches/v2/list-by-date"
    params = {
        "Category": sport_category,
        "Date": date_compact
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=14)
        if res.status_code != 200:
            return f"[!] Ошибка сервиса LiveScore: HTTP {res.status_code} ({res.text[:120]})"

        data = res.json()
        stages = data.get("Stages") or []

        if not stages:
            return f"Матчей по запросу <b>{sport_title}</b> на {date_label} ({date_display}) не найдено."

        filter_word = (league_filter or "").lower()

        raw_items = []
        for stage in stages:
            country = stage.get("Cnm", "")
            league = stage.get("Snm", "")
            full_league_name = f"{country} - {league}"

            if filter_word and (filter_word not in country.lower() and filter_word not in league.lower()):
                continue

            for event in stage.get("Events", []):
                t1 = event.get("T1", [{}])[0].get("Nm", "Команда 1")
                t2 = event.get("T2", [{}])[0].get("Nm", "Команда 2")

                score1 = event.get("Tr1", event.get("Tr1OR", "-"))
                score2 = event.get("Tr2", event.get("Tr2OR", "-"))
                match_status = event.get("Eps", event.get("Esd", ""))

                raw_items.append(f"[{full_league_name}] {t1} {score1}:{score2} {t2} (Статус: {match_status})")
                if len(raw_items) >= 28:
                    break
            if len(raw_items) >= 28:
                break

        if not raw_items:
            return f"Матчей в лиге <b>{league_filter.upper()}</b> на {date_label} ({date_display}) не найдено."

        raw_text = "\n".join(raw_items)

        translate_prompt = (
            f"Перед тобой перечень спортивных матчей ({sport_title}):\n"
            f'"""\n{raw_text}\n"""\n\n'
            "Переведи названия клубов, стран и турниров НА РУССКИЙ ЯЗЫК и сформируй аккуратный отчет.\n"
            "Правила:\n"
            "1. Сгруппируй по турнирам (РПЛ, АПЛ, Ла Лига, КХЛ, НХЛ и т.д.).\n"
            "2. Формат строки: 'Команда1 Счет : Счет Команда2 (статус / время)'.\n"
            "3. Статусы: FT / AET / AP -> 'Завершен', NS -> 'Не начался', минуты -> время игры.\n"
            "Сразу выдавай готовый список без лишних вступительных фраз."
        )

        translated = generate_ai_response(translate_prompt)
        icon = "\u26BD" if sport == "football" else "\U0001F3D2"
        return f"<b>{icon} {sport_title} ({date_label.upper()}, {date_display}):</b>\n\n{translated}"

    except Exception as e:
        return f"[!] Ошибка запроса матчей: {e}"

# --- КЛАВИАТУРЫ ---

def get_football_main_keyboard():
    keyboard = tele_types.InlineKeyboardMarkup(row_width=2)
    b_today = tele_types.InlineKeyboardButton("\U0001F4C5 Сегодня", callback_data="fb_dt_today")
    b_yesterday = tele_types.InlineKeyboardButton("\u23EA Вчера", callback_data="fb_dt_yesterday")
    b_tomorrow = tele_types.InlineKeyboardButton("\u23E9 Завтра", callback_data="fb_dt_tomorrow")
    b_custom = tele_types.InlineKeyboardButton("\U0001F5D3 Выбрать дату", callback_data="fb_custom")

    b_rpl = tele_types.InlineKeyboardButton("\U0001F1F7\U0001F1FA РПЛ (Россия)", callback_data="fb_lg_premier")
    b_apl = tele_types.InlineKeyboardButton("\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F АПЛ (Англия)", callback_data="fb_lg_premier league")
    b_laliga = tele_types.InlineKeyboardButton("\U0001F1EA\U0001F1F8 Ла Лига (Испания)", callback_data="fb_lg_laliga")
    b_seriea = tele_types.InlineKeyboardButton("\U0001F1EE\U0001F1F9 Серия А (Италия)", callback_data="fb_lg_serie a")
    b_buli = tele_types.InlineKeyboardButton("\U0001F1E9\U0001F1EA Бундеслига (Германия)", callback_data="fb_lg_bundesliga")
    b_ucl = tele_types.InlineKeyboardButton("\U0001F3C6 Лига Чемпионов", callback_data="fb_lg_champions league")

    keyboard.add(b_today, b_yesterday)
    keyboard.add(b_tomorrow, b_custom)
    keyboard.add(b_rpl, b_apl)
    keyboard.add(b_laliga, b_seriea)
    keyboard.add(b_buli, b_ucl)
    return keyboard

def get_hockey_main_keyboard():
    keyboard = tele_types.InlineKeyboardMarkup(row_width=2)
    b_today = tele_types.InlineKeyboardButton("\U0001F4C5 Сегодня", callback_data="hk_dt_today")
    b_yesterday = tele_types.InlineKeyboardButton("\u23EA Вчера", callback_data="hk_dt_yesterday")
    b_tomorrow = tele_types.InlineKeyboardButton("\u23E9 Завтра", callback_data="hk_dt_tomorrow")
    b_custom = tele_types.InlineKeyboardButton("\U0001F5D3 Выбрать дату", callback_data="hk_custom")

    b_khl = tele_types.InlineKeyboardButton("\U0001F1F7\U0001F1FA КХЛ", callback_data="hk_lg_khl")
    b_nhl = tele_types.InlineKeyboardButton("\U0001F1FA\U0001F1F8 / \U0001F1E8\U0001F1E6 НХЛ", callback_data="hk_lg_nhl")
    b_vhl = tele_types.InlineKeyboardButton("\U0001F1F7\U0001F1FA ВХЛ", callback_data="hk_lg_vhl")

    keyboard.add(b_today, b_yesterday)
    keyboard.add(b_tomorrow, b_custom)
    keyboard.add(b_khl, b_nhl)
    keyboard.add(b_vhl)
    return keyboard

def get_mode_keyboard():
    keyboard = tele_types.InlineKeyboardMarkup(row_width=2)
    b_def = tele_types.InlineKeyboardButton("\U0001F504 Дефолт", callback_data="setmode_дефолт")
    b_smart = tele_types.InlineKeyboardButton("\U0001F9E0 Умный", callback_data="setmode_умный")
    b_diana = tele_types.InlineKeyboardButton("\U0001F484 Диана", callback_data="setmode_диана")
    b_kardash = tele_types.InlineKeyboardButton("\U0001F953 Кардаш", callback_data="setmode_кардаш")
    b_perfumer = tele_types.InlineKeyboardButton("\U0001F9EA Парфюмер", callback_data="setmode_парфюмер")
    b_boss = tele_types.InlineKeyboardButton("\U0001F91F Тони (Босс)", callback_data="setmode_босс")
    b_prorab = tele_types.InlineKeyboardButton("\U0001F6E0 Прораб", callback_data="setmode_прораб")
    b_bratka = tele_types.InlineKeyboardButton("\U0001F44A Братка", callback_data="setmode_братка")
    b_dushnila = tele_types.InlineKeyboardButton("\U0001F913 Душнила", callback_data="setmode_душнила")
    b_sweet = tele_types.InlineKeyboardButton("\U0001F338 Милая", callback_data="setmode_милая")
    b_edward = tele_types.InlineKeyboardButton("\U0001F9DB Эдвард", callback_data="setmode_эдвард")
    keyboard.add(b_def, b_smart)
    keyboard.add(b_diana, b_kardash)
    keyboard.add(b_perfumer, b_boss)
    keyboard.add(b_prorab, b_bratka)
    keyboard.add(b_dushnila, b_sweet)
    keyboard.add(b_edward)
    return keyboard

# --- ОБРАБОТЧИКИ КОМАНД СПОРТА ---

@bot.message_handler(commands=['football', 'футбол'])
def handle_football_cmd(message):
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    clean_text = (message.text or "").replace(f"@{bot_username}", "").strip()
    parts = clean_text.split(maxsplit=1)

    if len(parts) == 1:
        bot.reply_to(
            message,
            "\u26BD <b>Футбольный центр:</b>\nВыберите день или интересующую лигу:",
            reply_markup=get_football_main_keyboard(),
            parse_mode="HTML"
        )
        return

    bot.send_chat_action(message.chat.id, "typing")
    result = fetch_sports_data("football", parts[1])
    bot.reply_to(message, result, parse_mode="HTML")

@bot.message_handler(commands=['hockey', 'хоккей'])
def handle_hockey_cmd(message):
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    clean_text = (message.text or "").replace(f"@{bot_username}", "").strip()
    parts = clean_text.split(maxsplit=1)

    if len(parts) == 1:
        bot.reply_to(
            message,
            "\U0001F3D2 <b>Хоккейный центр:</b>\nВыберите день или лигу (КХЛ, НХЛ, ВХЛ):",
            reply_markup=get_hockey_main_keyboard(),
            parse_mode="HTML"
        )
        return

    bot.send_chat_action(message.chat.id, "typing")
    result = fetch_sports_data("ice-hockey", parts[1])
    bot.reply_to(message, result, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("fb_", "hk_")))
def handle_sport_callbacks(call):
    is_football = call.data.startswith("fb_")
    sport_type = "football" if is_football else "ice-hockey"

    if call.data in ["fb_custom", "hk_custom"]:
        awaiting_custom_date[call.message.chat.id] = sport_type
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "<b>\U0001F5D3 Введите дату для поиска матчей:</b>\n(например: <code>15.10.2024</code> или <code>2024-11-05</code>):",
            parse_mode="HTML"
        )
        return

    bot.answer_callback_query(call.id, text="Загрузка матчей...")
    bot.send_chat_action(call.message.chat.id, "typing")

    mapping = {
        # Футбол: дни
        "fb_dt_today": ("сегодня", ""),
        "fb_dt_yesterday": ("вчера", ""),
        "fb_dt_tomorrow": ("завтра", ""),
        # Футбол: лиги
        "fb_lg_premier": ("сегодня", "premier"),
        "fb_lg_premier league": ("сегодня", "premier league"),
        "fb_lg_laliga": ("сегодня", "laliga"),
        "fb_lg_serie a": ("сегодня", "serie a"),
        "fb_lg_bundesliga": ("сегодня", "bundesliga"),
        "fb_lg_champions league": ("сегодня", "champions league"),
        # Хоккей: дни
        "hk_dt_today": ("сегодня", ""),
        "hk_dt_yesterday": ("вчера", ""),
        "hk_dt_tomorrow": ("завтра", ""),
        # Хоккей: лиги
        "hk_lg_khl": ("сегодня", "khl"),
        "hk_lg_nhl": ("сегодня", "nhl"),
        "hk_lg_vhl": ("сегодня", "vhl")
    }

    q, l_filter = mapping.get(call.data, ("сегодня", ""))
    result = fetch_sports_data(sport_type, q, l_filter)
    bot.send_message(call.message.chat.id, result, parse_mode="HTML")

# --- СВОДКИ СООБЩЕНИЙ ЧАТА ---

def build_summary_from_messages(logs) -> str:
    user_messages = defaultdict(list)
    for entry in logs:
        user_messages[entry['user']].append(entry['text'])

    users_digest = ""
    for u_name, msgs in user_messages.items():
        sample = " | ".join(msgs[-12:])
        users_digest += f"Участник [{u_name}] (сообщений: {len(msgs)}):\nЦитаты: \"{sample}\"\n\n"

    summary_prompt = (
        "Ты - остроумный, ироничный обозреватель и стендап-комик в Telegram-чате.\n"
        "Перед тобой сообщения участников за весь сегодняшний день, сгруппированные по каждому человеку:\n\n"
        f"{users_digest}\n"
        "Твоя задача - составить сочный, смешной и персонализированный 'ИТОГ ДНЯ В ЧАТЕ'.\n\n"
        "СТРОГАЯ СТРУКТУРА ОТЧЕТА:\n"
        "1. ПЕРСОНАЛЬНЫЙ РАЗБОР (пройдись ПО КАЖДОМУ пользователю отдельно):\n"
        "   - Назови участника через @ или имя.\n"
        "   - Выдай ему смешную номинацию (например: 'Экономист на такси', 'Ветеран Wildberries за 3500', 'Мисс токсичность').\n"
        "   - С юмором прокомментируй его поведение: на что жаловался, чем хвастался, где затупил или о чем спорил, опираясь на его реальные слова.\n\n"
        "2. ГЛАВНЫЙ СЮЖЕТ И СПЛЕТНИ ДНЯ:\n"
        "   - Опиши 1-2 главных конфликта или темы, вокруг которых бурлил чат.\n\n"
        "3. МОРАЛЬ НА НОЧЬ:\n"
        "   - Финальная смешная фраза перед сном.\n\n"
        "Пиши дерзко, весело, без канцелярита!"
    )
    return generate_ai_response(summary_prompt)

def scheduler_thread():
    moscow_tz = timezone(timedelta(hours=3))
    while True:
        try:
            now = datetime.now(moscow_tz)
            if now.hour == 23 and now.minute == 0:
                chats_to_process = list(daily_chat_logs.keys())
                for c_id in chats_to_process:
                    logs = daily_chat_logs.get(c_id, [])
                    if logs and len(logs) >= 3:
                        try:
                            summary_text = build_summary_from_messages(logs)
                            header = "<b>\U0001F31F ПЕРСОНАЛЬНЫЙ ИТОГ ДНЯ (23:00):</b>\n\n"
                            bot.send_message(c_id, header + summary_text, parse_mode="HTML")
                        except Exception as e:
                            print(f"Ошибка отправки итогов в чат {c_id}: {e}")
                    daily_chat_logs[c_id] = []
                time.sleep(70)
            else:
                time.sleep(25)
        except Exception as e:
            print(f"Ошибка в цикле планировщика: {e}")
            time.sleep(10)

@bot.message_handler(commands=['summary_test', 'тест_итоги'])
def handle_test_summary(message):
    bot.send_chat_action(message.chat.id, "typing")
    try:
        summary_text = build_summary_from_messages(MOCK_YESTERDAY_LOGS)
        bot.reply_to(message, f"<b>\U0001F3AD ТЕСТОВЫЙ РАЗБОР ПО УЧАСТНИКАМ:</b>\n\n{summary_text}", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['summary', 'итоги'])
def handle_live_summary(message):
    bot.send_chat_action(message.chat.id, "typing")
    logs = daily_chat_logs.get(message.chat.id, [])
    if not logs or len(logs) < 3:
        bot.reply_to(message, "Сегодня в чате пока маловато сообщений. Напишите пару фраз или проверьте через <code>/summary_test</code>!", parse_mode="HTML")
        return
    try:
        summary_text = build_summary_from_messages(logs)
        bot.reply_to(message, f"<b>\U0001F4CB ИТОГИ С РАЗБОРОМ ПО УЧАСТНИКАМ:</b>\n\n{summary_text}", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['mode', 'персонаж'])
def handle_mode_switch(message):
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    clean_text = (message.text or "").replace(f"@{bot_username}", "").strip()
    args = clean_text.split(maxsplit=1)

    if len(args) < 2:
        current = chat_modes.get(message.chat.id, "дефолт")
        bot.reply_to(
            message,
            f"Текущий режим чата: <b>{current.upper()}</b>\n\n"
            "Выберите желаемую роль кнопкой ниже:",
            reply_markup=get_mode_keyboard(),
            parse_mode="HTML"
        )
        return

    selected = args[1].strip().lower()
    if selected in CHARACTERS:
        chat_modes[message.chat.id] = selected
        bot.reply_to(message, f"Режим успешно включен: <b>{selected.upper()}</b>!", parse_mode="HTML")
    else:
        bot.reply_to(message, f"Не знаю роли '{selected}'.", reply_markup=get_mode_keyboard(), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("setmode_"))
def handle_mode_callback(call):
    new_mode = call.data.replace("setmode_", "").strip().lower()
    chat_modes[call.message.chat.id] = new_mode
    bot.answer_callback_query(call.id, text=f"Режим переключен на: {new_mode.upper()}")
    bot.send_message(call.message.chat.id, f"\U0001F3AD Режим успешно включен: <b>{new_mode.upper()}</b>!", parse_mode="HTML")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    caption = message.caption or ""
    sender_username = message.from_user.username
    sender_info = f"@{sender_username}" if sender_username else (message.from_user.first_name or "Участник")

    daily_chat_logs[message.chat.id].append({
        "user": sender_info,
        "text": f"[Фото]: {caption}" if caption else "[Фото]"
    })

    if not check_group_trigger(message, caption):
        return

    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "Legendariki_chat_bot"

    prompt = caption.replace(f"@{bot_username}", "").strip()
    if not prompt:
        prompt = "Опиши, что изображено на фото, проанализируй свойства и дай совет."

    current_role = chat_modes.get(message.chat.id, "дефолт")

    if current_role != "дефолт":
        lower_prompt = prompt.lower()
        if "диан" in lower_prompt:
            current_role = "диана"
        elif any(k in lower_prompt for k in ["кардаш", "жиробас", "никит"]):
            current_role = "кардаш"
        elif any(k in lower_prompt for k in ["парфюм", "духи", "аромат"]):
            current_role = "парфюмер"
        elif any(k in lower_prompt for k in ["эдвард", "сумерк", "каллен"]):
            current_role = "эдвард"

    system_instruction = CHARACTERS.get(current_role, "")
    brevity = "" if current_role in ["умный", "парфюмер"] else f"{BREVITY_RULE}\n\n"

    role_block = f"ИНСТРУКЦИЯ ПО РОЛИ:\n{system_instruction}\n\n" if system_instruction else ""
    user_context = f"{brevity}{role_block}[Автор запроса: {sender_info}]\nВопрос к фото: {prompt}"

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_text = message.reply_to_message.text or ""
        if len(prev_text) > 1200:
            prev_text = prev_text[:1200] + "..."
        final_prompt = f'Контекст твоего предыдущего ответа:\n"""{prev_text}"""\n\n{user_context}'
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

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text or ""
    sender_username = message.from_user.username
    sender_info = f"@{sender_username}" if sender_username else (message.from_user.first_name or "Участник")

    if not user_text.startswith("/"):
        daily_chat_logs[message.chat.id].append({
            "user": sender_info,
            "text": user_text
        })
        if len(daily_chat_logs[message.chat.id]) > 400:
            daily_chat_logs[message.chat.id].pop(0)

    if message.chat.id in awaiting_custom_date and not user_text.startswith("/"):
        sport_target = awaiting_custom_date.pop(message.chat.id)
        bot.send_chat_action(message.chat.id, "typing")
        result = fetch_sports_data(sport_target, user_text)
        bot.reply_to(message, result, parse_mode="HTML")
        return

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

    if current_role != "дефолт":
        lower_prompt = prompt.lower()
        if "диан" in lower_prompt:
            current_role = "диана"
        elif any(k in lower_prompt for k in ["кардаш", "жиробас", "никит"]):
            current_role = "кардаш"
        elif any(k in lower_prompt for k in ["парфюм", "духи", "аромат"]):
            current_role = "парфюмер"
        elif any(k in lower_prompt for k in ["эдвард", "сумерк", "каллен"]):
            current_role = "эдвард"

    system_instruction = CHARACTERS.get(current_role, "")
    brevity = "" if current_role in ["умный", "парфюмер"] else f"{BREVITY_RULE}\n\n"

    role_block = f"ИНСТРУКЦИЯ ПО РОЛИ:\n{system_instruction}\n\n" if system_instruction else ""
    user_context = f"{brevity}{role_block}[Пишет пользователь: {sender_info}]\nСообщение: {prompt}"

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        prev_bot_reply = message.reply_to_message.text or ""
        if len(prev_bot_reply) > 1500:
            prev_bot_reply = prev_bot_reply[:1500] + "..."

        final_prompt = (
            f'Контекст твоего предыдущего ответа:\n"""{prev_bot_reply}"""\n\n'
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

def setup_bot_commands():
    commands = [
        tele_types.BotCommand("football", "Футбол (счет, вчера/сегодня/завтра, лиги)"),
        tele_types.BotCommand("hockey", "Хоккей (КХЛ, НХЛ, ВХЛ, счет)"),
        tele_types.BotCommand("mode", "Выбрать персонажа"),
        tele_types.BotCommand("summary", "Итог дня в чате"),
        tele_types.BotCommand("summary_test", "Тест сводки со стендапом")
    ]
    try:
        bot.set_my_commands(commands)
    except Exception as e:
        print(f"Ошибка установки команд меню: {e}")

def run_telebot():
    print("Инициализация Telegram polling...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
    except Exception:
        pass

    setup_bot_commands()
    print("Telegram polling запущен...")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"Сбой polling: {e}. Перезапуск через 3 сек...")
            time.sleep(3)

if __name__ == "__main__":
    t_bot = threading.Thread(target=run_telebot, daemon=True)
    t_bot.start()

    t_sched = threading.Thread(target=scheduler_thread, daemon=True)
    t_sched.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

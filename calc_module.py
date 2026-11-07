import os
import telebot

# Ваш ID в Telegram
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))

user_calc_sessions = {}


def build_warehouse_checklist(data: dict) -> str:
    """Формирует точный складской сборочный лист под параметры скважины."""
    depth = data["depth"]
    yield_flow = data["yield_flow"]
    houses = data["houses"]
    distance = data["distance"]

    # Инженерный расчёт
    pump_depth = max(10, int(depth - 5))
    total_pipe_run = pump_depth + distance
    friction_losses = total_pipe_run * 0.10
    required_head = int(pump_depth + friction_losses + 30 + 5)

    # 1. Насос
    if required_head <= 60:
        pump_model = "Насос скважинный 3\"/4\" (напор 60-70 м, 2.5-3.0 м³/ч)"
    elif required_head <= 85:
        pump_model = "Насос скважинный 3\"/4\" (напор 80-90 м, 3.0-3.5 м³/ч)"
    elif required_head <= 110:
        pump_model = "Насос скважинный усиленный (напор 100-115 м)"
    else:
        pump_model = "Насос высоконапорный промышленной серии (напор 120+ м)"

    # 2. Кессон
    if houses == 1:
        kesson_name = "Кессон пластиковый «МИШКА-2» (1000х2000 мм)"
        branch_tees = 1
    else:
        kesson_name = f"Кессон пластиковый «МИШКА-3» (увеличенный под гребёнку на {houses} вывода)"
        branch_tees = houses

    # 3. Гидробак
    if houses == 1:
        tank_spec = "Гидроаккумулятор 80-100 л (вертикальный, фланец нерж)"
    elif houses == 2:
        tank_spec = "Гидроаккумулятор 150 л (или 2 шт. по 80-100 л)"
    else:
        tank_spec = f"Гидроаккумулятор 200-300 л (под {houses} домов)"

    # Метражи
    pnd_downhole = int(pump_depth * 1.05)
    pnd_trench = int(distance * houses * 1.05)
    total_pnd_pipe = pnd_downhole + pnd_trench + 5  # с запасом на подъёмы
    cable_m = int((pump_depth + 5) * 1.1)
    rope_m = int(pump_depth + 6)
    cable_ties = max(40, int(pump_depth * 1.5))
    insulation_m = int(distance * houses + 2)

    # Собираем чек-лист склада
    checklist = (
        f"📦 <b>ЗАКАЗ НА СБОРКУ СКЛАДА (СБОРКА КОМПЛЕКТА)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👷 <b>Монтажник:</b> {data['worker_name']} ({data['worker_tag']})\n"
        f"🆔 ID чата: <code>{data['chat_id']}</code>\n\n"
        f"📋 <b>Входные параметры объекта:</b>\n"
        f"• Глубина скважины: <b>{depth} м</b> (подвеска насоса на {pump_depth} м)\n"
        f"• Дебит: <b>{yield_flow} м³/ч</b> | Расчётный напор: <b>{required_head} м</b>\n"
        f"• Подключение домов: <b>{houses} шт.</b>\n"
        f"• Расстояние до объекта: <b>{distance} м</b>\n\n"
        f"🛠 <b>СПИСОК НА ОТГРУЗКУ:</b>\n\n"
        f"<b>1. Кессон и устье:</b>\n"
        f"  ▫️ {kesson_name} — 1 шт.\n"
        f"  ▫️ Муфта обсадной трубы герметичная (под обсадную) — 1 шт.\n"
        f"  ▫️ Оголовок скважинный герметичный 125-133/32 — 1 шт.\n"
        f"  ▫️ Гермовводы для ПНД 32 в кессон — {houses + 1} шт. (трасса + полив)\n\n"
        f"<b>2. Спускной скважинный узел:</b>\n"
        f"  ▫️ {pump_model} — 1 шт.\n"
        f"  ▫️ Трос нержавеющий А2/А4 (Ø4 мм) — <b>{rope_m} м</b>\n"
        f"  ▫️ Зажимы троса нержавеющие (дуплекс 4 мм) — 4 шт.\n"
        f"  ▫️ Коуши нержавеющие 4 мм — 2 шт.\n"
        f"  ▫️ Карабин нержавеющий 8 мм — 1 шт.\n"
        f"  ▫️ Обратный клапан латунный 1\" (латунный шток) — 1 шт.\n"
        f"  ▫️ Ниппель латунный 1\" НР-НР — 1 шт.\n"
        f"  ▫️ Муфта латунная компрессионная ПНД 32 х 1\" НР — 1 шт.\n\n"
        f"<b>3. Труба, кабель и расходка:</b>\n"
        f"  ▫️ Труба питьевая ПНД PE-100 SDR11 Ø32 мм — <b>{total_pnd_pipe} м</b> (бухта)\n"
        f"  ▫️ Кабель водопогружной КВВ-П 3х2.5 — <b>{cable_m} м</b>\n"
        f"  ▫️ Муфта кабельная термоусадочная заливная/клеевая — 1 компл.\n"
        f"  ▫️ Стяжки нейлоновые уличные (черные) — {cable_ties} шт.\n"
        f"  ▫️ Утеплитель для ПНД 32 (энергофлекс 9-13 мм) — <b>{insulation_m} м</b>\n\n"
        f"<b>4. Автоматика и обвязка:</b>\n"
        f"  ▫️ {tank_spec} — 1 шт.\n"
        f"  ▫️ Пятивыводной штуцер (пятерник) 1\" латунь — {branch_tees} шт.\n"
        f"  ▫️ Реле давления (Italtecnica PM/5G или Турбипресс) — 1 шт.\n"
        f"  ▫️ Манометр 0-6 бар (1/4\") — 1 шт.\n"
        f"  ▫️ Фильтр магистральный BB10/BB20 (1\") с картриджем — 1 шт.\n"
        f"  ▫️ Краны шаровые латунные 1\" (с американкой) — {2 * houses} шт.\n"
        f"  ▫️ Кран летнего полива 3/4\" со штуцером — 1 шт.\n"
        f"  ▫️ Греющий кабель саморегулирующийся (ввод в дом) — {houses * 2} м + муфты\n"
    )
    return checklist


def register_calc_handlers(bot):

    @bot.message_handler(commands=['calc', 'smeta'])
    def start_calc(message):
        user_calc_sessions[message.chat.id] = {}
        bot.reply_to(
            message,
            "🔧 <b>Параметры скважины для выдачи комплекта:</b>\n\n"
            "1️⃣ <b>Глубина скважины (в метрах):</b>\n<i>(введите число, например: 40)</i>",
            parse_mode="HTML"
        )
        bot.register_next_step_handler(message, lambda m: step_depth(m, bot))

    def step_depth(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = float(message.text.replace(",", "."))
            if val <= 0 or val > 300:
                raise ValueError
            user_calc_sessions[message.chat.id]["depth"] = val
            bot.reply_to(
                message,
                "2️⃣ <b>Дебит (производительность) скважины в м³/час:</b>\n<i>(если не знаешь точно — пиши 2 или 3)</i>",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(message, lambda m: step_yield(m, bot))
        except (ValueError, TypeError):
            bot.reply_to(message, "⚠️ Введи глубину числом (например: 40):")
            bot.register_next_step_handler(message, lambda m: step_depth(m, bot))

    def step_yield(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = float(message.text.replace(",", "."))
            if val <= 0 or val > 50:
                raise ValueError
            user_calc_sessions[message.chat.id]["yield_flow"] = val
            bot.reply_to(
                message,
                "3️⃣ <b>Сколько строений (домов) подключаем?</b>\n<i>(введи число, например: 1)</i>",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(message, lambda m: step_houses(m, bot))
        except (ValueError, TypeError):
            bot.reply_to(message, "⚠️ Введи число дебита (например: 2.5):")
            bot.register_next_step_handler(message, lambda m: step_yield(m, bot))

    def step_houses(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = int(message.text.strip())
            if val < 1 or val > 10:
                raise ValueError
            user_calc_sessions[message.chat.id]["houses"] = val
            bot.reply_to(
                message,
                "4️⃣ <b>Расстояние от скважины до дома (в метрах):</b>\n<i>(например: 15)</i>",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(message, lambda m: step_distance(m, bot))
        except (ValueError, TypeError):
            bot.reply_to(message, "⚠️ Введи количество домов целым числом (например: 1):")
            bot.register_next_step_handler(message, lambda m: step_houses(m, bot))

    def step_distance(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = float(message.text.replace(",", "."))
            if val < 0 or val > 1000:
                raise ValueError
            user_calc_sessions[message.chat.id]["distance"] = val

            data = user_calc_sessions.get(message.chat.id, {})
            data["worker_tag"] = f"@{message.from_user.username}" if message.from_user.username else "нет username"
            data["worker_name"] = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "Монтажник"
            data["chat_id"] = message.chat.id

            # 1. Ответ монтажнику в чат
            bot.reply_to(
                message,
                "✅ <b>Спасибо! Запрос принят.</b>\n"
                "Спецификация передана на склад, начинаем комплектовать заказ к вашему приезду.",
                parse_mode="HTML"
            )

            # 2. Формируем подробный сборочный лист и шлём вам в ЛС
            checklist = build_warehouse_checklist(data)
            try:
                bot.send_message(ADMIN_CHAT_ID, checklist, parse_mode="HTML")
            except Exception as e:
                print(f"[ERROR] Не удалось отправить сборочный лист админу {ADMIN_CHAT_ID}: {e}")

        except (ValueError, TypeError):
            bot.reply_to(message, "⚠️ Введи расстояние числом метров (например: 15):")
            bot.register_next_step_handler(message, lambda m: step_distance(m, bot))

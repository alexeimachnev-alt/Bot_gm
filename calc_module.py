import os
import telebot

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))

user_calc_sessions = {}


def build_warehouse_checklist(data: dict) -> str:
    """Формирует складской сборочный лист под параметры скважины и трасс."""
    depth = data["depth"]
    yield_flow = data["yield_flow"]
    houses = data["houses"]
    distances = data["distances"]  # Список расстояний до каждого дома [d1, d2, ...]

    total_distance = sum(distances)
    max_distance = max(distances)

    # Инженерный расчёт
    pump_depth = max(10, int(depth - 5))
    total_pipe_run = pump_depth + max_distance
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
        kesson_name = f"Кессон пластиковый «МИШКА-3» (увеличенный с гребёнкой на {houses} вывода)"
        branch_tees = houses

    # 3. Гидроаккумулятор
    if houses == 1:
        tank_spec = "Гидроаккумулятор 80-100 л (вертикальный, фланец нерж)"
    elif houses == 2:
        tank_spec = "Гидроаккумулятор 150 л (или 2 шт. по 80-100 л)"
    else:
        tank_spec = f"Гидроаккумулятор 200-300 л (под {houses} домов)"

    # Метражи
    pnd_downhole = int(pump_depth * 1.05)
    pnd_trench = int(total_distance * 1.05)
    total_pnd_pipe = pnd_downhole + pnd_trench + (houses * 4)  # с запасом на вводы в фундаменты
    cable_m = int((pump_depth + 5) * 1.1)
    rope_m = int(pump_depth + 6)
    cable_ties = max(40, int(pump_depth * 1.5))
    insulation_m = int(total_distance + (houses * 2))

    # Формируем строку с детализацией трасс
    if houses == 1:
        routes_detail = f"• Трасса до дома: <b>{distances[0]} м</b>\n"
    else:
        routes_detail = f"• Домов: <b>{houses} шт.</b> (общая длина трасс: <b>{total_distance} м</b>):\n"
        for idx, d in enumerate(distances, start=1):
            routes_detail += f"   ▫️ Дом №{idx}: <b>{d} м</b>\n"

    checklist = (
        f"📦 <b>ЗАКАЗ НА СКЛАДСКУЮ СБОРКУ КОМПЛЕКТА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👷 <b>Монтажник:</b> {data['worker_name']} ({data['worker_tag']})\n"
        f"🆔 ID чата: <code>{data['chat_id']}</code>\n\n"
        f"📋 <b>Входные параметры объекта:</b>\n"
        f"• Глубина скважины: <b>{depth} м</b> (подвеска насоса на ~{pump_depth} м)\n"
        f"• Дебит: <b>{yield_flow} м³/ч</b> | Расчётный напор: <b>{required_head} м</b>\n"
        f"{routes_detail}\n"
        f"🛠 <b>СПИСОК НА ОТГРУЗКУ (ДО ВИНТИКА):</b>\n\n"
        f"<b>1. Кессон и устье:</b>\n"
        f"  ▫️ {kesson_name} — 1 шт.\n"
        f"  ▫️ Муфта обсадной трубы герметичная — 1 шт.\n"
        f"  ▫️ Оголовок скважинный 125-133/32 — 1 шт.\n"
        f"  ▫️ Гермовводы для ПНД 32 в стенки кессона — {houses + 1} шт. (трассы + полив)\n\n"
        f"<b>2. Спускной скважинный узел:</b>\n"
        f"  ▫️ {pump_model} — 1 шт.\n"
        f"  ▫️ Трос нержавеющий А2/А4 (Ø4 мм) — <b>{rope_m} м</b>\n"
        f"  ▫️ Зажимы троса нержавеющие дуплекс 4 мм — 4 шт.\n"
        f"  ▫️ Коуши нержавеющие 4 мм — 2 шт.\n"
        f"  ▫️ Карабин винтовой нержавеющий 8 мм — 1 шт.\n"
        f"  ▫️ Обратный клапан латунный 1\" — 1 шт.\n"
        f"  ▫️ Ниппель латунный 1\" НР-НР — 1 шт.\n"
        f"  ▫️ Муфта латунная компрессионная ПНД 32 х 1\" НР — 1 шт.\n\n"
        f"<b>3. Труба, кабель и изоляция:</b>\n"
        f"  ▫️ Труба питьевая ПНД PE-100 SDR11 Ø32 мм — <b>{total_pnd_pipe} м</b>\n"
        f"  ▫️ Кабель водопогружной КВВ-П 3х2.5 — <b>{cable_m} м</b>\n"
        f"  ▫️ Термоусадочная клеевая кабельная муфта — 1 компл.\n"
        f"  ▫️ Стяжки нейлоновые уличные черные — {cable_ties} шт.\n"
        f"  ▫️ Утеплитель для ПНД 32 (энергофлекс 9-13 мм) — <b>{insulation_m} м</b>\n\n"
        f"<b>4. Автоматика и разводка:</b>\n"
        f"  ▫️ {tank_spec} — 1 шт.\n"
        f"  ▫️ Пятивыводной штуцер (пятерник) 1\" латунь — {branch_tees} шт.\n"
        f"  ▫️ Реле давления (Italtecnica / Турбипресс) — 1 шт.\n"
        f"  ▫️ Манометр 0-6 бар (1/4\") — 1 шт.\n"
        f"  ▫️ Магистральный фильтр BB10/BB20 (1\") + картридж — 1 шт.\n"
        f"  ▫️ Краны шаровые латунные 1\" (с американкой) — {2 * houses} шт.\n"
        f"  ▫️ Кран летнего полива 3/4\" со штуцером — 1 шт.\n"
        f"  ▫️ Греющий кабель саморегулирующийся (вводы в дома) — <b>{houses * 3} м</b> + {houses} сальниковых узлов\n"
    )
    return checklist


def register_calc_handlers(bot):

    @bot.message_handler(commands=['calc', 'smeta'])
    def start_calc(message):
        user_calc_sessions[message.chat.id] = {"distances": []}
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
                "2️⃣ <b>Дебит (производительность) скважины в м³/час:</b>\n<i>(по паспорту, либо в среднем: 2 или 3)</i>",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(message, lambda m: step_yield(m, bot))
        except (ValueError, TypeError):
            bot.reply_to(message, "⚠️ Введите глубину числом (например: 40):")
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
                "3️⃣ <b>Сколько строений (домов) подключаем?</b>\n<i>(введите число, например: 1 или 2)</i>",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(message, lambda m: step_houses(m, bot))
        except (ValueError, TypeError):
            bot.reply_to(message, "⚠️ Введите дебит числом (например: 2.5):")
            bot.register_next_step_handler(message, lambda m: step_yield(m, bot))

    def step_houses(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = int(message.text.strip())
            if val < 1 or val > 10:
                raise ValueError
            user_calc_sessions[message.chat.id]["houses"] = val
            user_calc_sessions[message.chat.id]["distances"] = []

            # Если дом один — обычный вопрос
            if val == 1:
                bot.reply_to(
                    message,
                    "4️⃣ <b>Расстояние от скважины до дома (в метрах):</b>\n<i>(например: 15)</i>",
                    parse_mode="HTML"
                )
                bot.register_next_step_handler(message, lambda m: step_single_distance(m, bot))
            else:
                # Если домов больше 1 — запускаем опрос по каждому дому
                bot.reply_to(
                    message,
                    "4️⃣ <b>Расстояние от скважины до Дома №1 (в метрах):</b>\n<i>(например: 15)</i>",
                    parse_mode="HTML"
                )
                bot.register_next_step_handler(message, lambda m: step_multi_distance(m, bot, house_idx=1))
        except (ValueError, TypeError):
            bot.reply_to(message, "⚠️ Введите количество домов целым числом (например: 1):")
            bot.register_next_step_handler(message, lambda m: step_houses(m, bot))

    def step_single_distance(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = float(message.text.replace(",", "."))
            if val < 0 or val > 1000:
                raise ValueError
            user_calc_sessions[message.chat.id]["distances"] = [val]
            finish_collection(message, bot)
        except (ValueError, TypeError):
            bot.reply_to(message, "⚠️ Введите расстояние числом метров (например: 15):")
            bot.register_next_step_handler(message, lambda m: step_single_distance(m, bot))

    def step_multi_distance(message, bot, house_idx):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = float(message.text.replace(",", "."))
            if val < 0 or val > 1000:
                raise ValueError

            user_calc_sessions[message.chat.id]["distances"].append(val)
            total_houses = user_calc_sessions[message.chat.id]["houses"]

            # Если ещё остались дома
            if house_idx < total_houses:
                next_house = house_idx + 1
                bot.reply_to(
                    message,
                    f"▫️ <b>Расстояние от скважины до Дома №{next_house} (в метрах):</b>\n<i>(например: 25)</i>",
                    parse_mode="HTML"
                )
                bot.register_next_step_handler(message, lambda m: step_multi_distance(m, bot, house_idx=next_house))
            else:
                # Все расстояния собраны
                finish_collection(message, bot)
        except (ValueError, TypeError):
            bot.reply_to(message, f"⚠️ Введите расстояние для Дома №{house_idx} числом (например: 20):")
            bot.register_next_step_handler(message, lambda m: step_multi_distance(m, bot, house_idx=house_idx))

    def finish_collection(message, bot):
        data = user_calc_sessions.get(message.chat.id, {})
        data["worker_tag"] = f"@{message.from_user.username}" if message.from_user.username else "нет username"
        data["worker_name"] = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "Монтажник"
        data["chat_id"] = message.chat.id

        # Ответ монтажнику
        bot.reply_to(
            message,
            "✅ <b>Спасибо! Запрос принят.</b>\n"
            "Спецификация передана на склад, начинаем комплектовать заказ к вашему приезду.",
            parse_mode="HTML"
        )

        # Отправка подробного сборочного листа вам в ЛС
        checklist = build_warehouse_checklist(data)
        try:
            bot.send_message(ADMIN_CHAT_ID, checklist, parse_mode="HTML")
            print(f"[SUCCESS] Сборочный лист отправлен админу {ADMIN_CHAT_ID}")
        except Exception as e:
            print(f"[ERROR] Ошибка отправки админу {ADMIN_CHAT_ID}: {e}")

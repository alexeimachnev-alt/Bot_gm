import os
from telebot import types

# Ваш ID зашит по умолчанию, также может читаться из переменных окружения
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))

user_calc_sessions = {}


def calculate_estimate(data: dict) -> dict:
    depth = data["depth"]
    yield_flow = data["yield_flow"]
    houses = data["houses"]
    distance = data["distance"]

    # 1. Расчёт глубины спуска и требуемого напора
    pump_depth = max(10, int(depth - 5))
    total_pipe_run = pump_depth + distance
    friction_losses = total_pipe_run * 0.10
    required_head = int(pump_depth + friction_losses + 30 + 5)

    # 2. Подбор класса насоса по напору
    if required_head <= 60:
        pump_model = "Скважинный насос напор 60-70 м (3.0 м³/ч)"
        pump_cost = 26000
    elif required_head <= 85:
        pump_model = "Скважинный насос напор 80-90 м (3.5 м³/ч)"
        pump_cost = 34000
    elif required_head <= 110:
        pump_model = "Скважинный насос усиленный 100-115 м"
        pump_cost = 45000
    else:
        pump_model = "Высоконапорный насос 120+ м / пром. серия"
        pump_cost = 62000

    # 3. Подбор гидробака под число точек/домов
    if houses == 1:
        tank_spec = "Гидроаккумулятор 80-100 л (нерж. фланец)"
        tank_cost = 14000
    elif houses == 2:
        tank_spec = "Гидроаккумулятор 150 л (или 2х80 л)"
        tank_cost = 24000
    else:
        tank_spec = f"Гидроаккумулятор 200-300 л (на {houses} домов)"
        tank_cost = 38000

    # 4. Метражи спуска и материалов
    pipe_downhole_m = int(pump_depth * 1.1)
    cable_downhole_m = int((pump_depth + 5) * 1.1)
    rope_stainless_m = int(pump_depth + 6)

    # Смета водоподъема (ПНД 32 SDR11, нерж трос 4мм, кабель КВВ-П + оголовок и клапан)
    downhole_materials = (pipe_downhole_m * 110) + (rope_stainless_m * 130) + (cable_downhole_m * 160) + 9500

    # Трасса: траншея + труба ПНД 32 в энергофлексе (1200 руб/м)
    total_trench_distance = int(distance * houses)
    trench_cost = total_trench_distance * 1200

    # Подбор кессона
    if houses == 1:
        kesson_name = "Кессон пластиковый «МИШКА-2» с обжимной муфтой"
        kesson_cost = 48000
    else:
        kesson_name = "Кессон пластиковый «МИШКА-3» (увеличенный под гребёнку)"
        kesson_cost = 58000

    automation_kit_cost = tank_cost + 9000
    total_sum = pump_cost + downhole_materials + trench_cost + kesson_cost + automation_kit_cost

    return {
        "pump_model": pump_model,
        "pump_depth": pump_depth,
        "required_head": required_head,
        "tank_spec": tank_spec,
        "kesson_name": kesson_name,
        "pipe_downhole_m": pipe_downhole_m,
        "rope_stainless_m": rope_stainless_m,
        "total_distance": total_trench_distance,
        "pump_cost": pump_cost,
        "downhole_kit": downhole_materials,
        "trench_cost": trench_cost,
        "kesson_cost": kesson_cost,
        "automation_cost": automation_kit_cost,
        "total_sum": total_sum
    }


def register_calc_handlers(bot):
    """Регистрирует цепочку шагов калькулятора."""

    @bot.message_handler(commands=['calc', 'smeta'])
    def start_calc(message):
        user_calc_sessions[message.chat.id] = {}
        bot.send_message(
            message.chat.id,
            "💧 **Инженерный расчёт скважины с кессоном**\n\n"
            "Ответьте на 4 вопроса для точного подбора оборудования и сметы.\n\n"
            "1️⃣ **Какая глубина скважины в метрах?** (введите число, например: `40`):",
            parse_mode="Markdown"
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
            bot.send_message(
                message.chat.id,
                "2️⃣ **Какой дебит (производительность) скважины в м³/час?**\n"
                "*(По паспорту скважины, либо укажите среднее: `2` или `3`)*:",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(message, lambda m: step_yield(m, bot))
        except (ValueError, TypeError):
            bot.send_message(message.chat.id, "⚠️ Укажите глубину числом (например: 40):")
            bot.register_next_step_handler(message, lambda m: step_depth(m, bot))

    def step_yield(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = float(message.text.replace(",", "."))
            if val <= 0 or val > 50:
                raise ValueError
            user_calc_sessions[message.chat.id]["yield_flow"] = val
            bot.send_message(
                message.chat.id,
                "3️⃣ **Сколько домов / строений нужно подключить?** (число, например: `1`):",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(message, lambda m: step_houses(m, bot))
        except (ValueError, TypeError):
            bot.send_message(message.chat.id, "⚠️ Укажите производительность числом (например: 2.5):")
            bot.register_next_step_handler(message, lambda m: step_yield(m, bot))

    def step_houses(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = int(message.text.strip())
            if val < 1 or val > 10:
                raise ValueError
            user_calc_sessions[message.chat.id]["houses"] = val
            bot.send_message(
                message.chat.id,
                "4️⃣ **Какое расстояние от скважины до дома в метрах?** (например: `15`):",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(message, lambda m: step_distance(m, bot))
        except (ValueError, TypeError):
            bot.send_message(message.chat.id, "⚠️ Введите количество домов целым числом (например: 1):")
            bot.register_next_step_handler(message, lambda m: step_houses(m, bot))

    def step_distance(message, bot):
        if message.text and message.text.startswith('/'):
            return
        try:
            val = float(message.text.replace(",", "."))
            if val < 0 or val > 1000:
                raise ValueError
            user_calc_sessions[message.chat.id]["distance"] = val

            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            btn_phone = types.KeyboardButton(text="📱 Отправить контакт", request_contact=True)
            markup.add(btn_phone)

            bot.send_message(
                message.chat.id,
                "Все данные приняты! Нажмите кнопку ниже или отправьте номер телефона сообщением для получения сметы:",
                reply_markup=markup
            )
            bot.register_next_step_handler(message, lambda m: step_contact(m, bot))
        except (ValueError, TypeError):
            bot.send_message(message.chat.id, "⚠️ Введите расстояние числом метров (например: 15):")
            bot.register_next_step_handler(message, lambda m: step_distance(m, bot))

    def step_contact(message, bot):
        phone = ""
        if message.contact:
            phone = message.contact.phone_number
        elif message.text:
            phone = message.text.strip()
        else:
            phone = "Не указан"

        data = user_calc_sessions.get(message.chat.id, {})
        if not data:
            bot.send_message(message.chat.id, "Сессия устарела. Наберите /calc заново.")
            return

        data["phone"] = phone
        estimate = calculate_estimate(data)

        client_username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
        client_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

        # Полная смета инженеру (вам)
        admin_report = (
            f"🚨 **НОВАЯ ЗАЯВКА НА СМЕТУ СКВАЖИНЫ!**\n"
            f"👤 Клиент: {client_name} ({client_username})\n"
            f"📞 Телефон: `{phone}`\n"
            f"🆔 ID: `{message.chat.id}`\n\n"
            f"📋 **Входные данные:**\n"
            f"• Глубина: {data['depth']} м (спуск насоса: ~{estimate['pump_depth']} м)\n"
            f"• Дебит: {data['yield_flow']} м³/ч\n"
            f"• Домов: {data['houses']} шт.\n"
            f"• Трасса: {data['distance']} м (суммарно: {estimate['total_distance']} м)\n"
            f"• Расчётный напор: **{estimate['required_head']} м**\n\n"
            f"⚙️ **Подобранное оборудование:**\n"
            f"• {estimate['kesson_name']}\n"
            f"• {estimate['pump_model']}\n"
            f"• {estimate['tank_spec']}\n"
            f"• Труба ПНД 32 SDR11 в скважину: {estimate['pipe_downhole_m']} м\n"
            f"• Трос нерж. 4 мм: {estimate['rope_stainless_m']} м\n\n"
            f"💰 **Смета:**\n"
            f"• Кессон: {estimate['kesson_cost']:,} руб.\n"
            f"• Насос: {estimate['pump_cost']:,} руб.\n"
            f"• Водоподъёмный узел: {estimate['downhole_kit']:,} руб.\n"
            f"• Трасса водопровода: {estimate['trench_cost']:,} руб.\n"
            f"• Автоматика: {estimate['automation_cost']:,} руб.\n"
            f"──────────────\n"
            f"🔥 **ИТОГО: {estimate['total_sum']:,} руб.**"
        )

        # Сообщение заказчику
        client_message = (
            f"✅ **Предварительный расчёт скважины готов!**\n\n"
            f"• Глубина: **{data['depth']} м** (насос на глубине ~{estimate['pump_depth']} м)\n"
            f"• Подключение: **{data['houses']} дом(а)**\n"
            f"• Трасса водопровода: **{data['distance']} м**\n\n"
            f"📦 **Комплект под ключ включает:**\n"
            f"— {estimate['kesson_name']}\n"
            f"— {estimate['pump_model']}\n"
            f"— Питьевая труба ПНД 32 SDR11 + нержавеющий трос 4 мм\n"
            f"— {estimate['tank_spec']} + реле, манометр и фильтрация\n"
            f"— Земляные работы и прокладка утеплённой трассы до дома\n\n"
            f"💵 Ориентировочная стоимость под ключ: **~{estimate['total_sum']:,} руб.**\n\n"
            f"Инженер получил вашу спецификацию и свяжется с вами для согласования деталей!"
        )

        remove_markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, client_message, parse_mode="Markdown", reply_markup=remove_markup)

        try:
            bot.send_message(ADMIN_CHAT_ID, admin_report, parse_mode="Markdown")
        except Exception as e:
            print(f"[ERROR] Не удалось отправить смету админу {ADMIN_CHAT_ID}: {e}")

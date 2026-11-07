def calculate_estimate(data: dict) -> dict:
    depth = data["depth"]
    yield_flow = data["yield_flow"]
    houses = data["houses"]
    distance = data["distance"]

    # 1. Инженерный расчёт глубины и напора
    pump_depth = max(10, depth - 5)  # точка висения насоса
    total_pipe_run = pump_depth + distance
    friction_losses = total_pipe_run * 0.10  # 10% на трение в фитингах и трубе
    required_head = int(pump_depth + friction_losses + 30 + 5)  # +30м (3 атм в доме) + 5м на подъем в доме

    # 2. Автоматический подбор класса насоса
    if required_head <= 60:
        pump_model = "Скважинный насос напор 60-70 м (3 м³/ч)"
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

    # 3. Подбор гидробака в зависимости от количества домов
    if houses == 1:
        tank_spec = "Гидроаккумулятор 80-100 л (нерж. фланец)"
        tank_cost = 14000
    elif houses == 2:
        tank_spec = "Гидроаккумулятор 150 л (или 2х80 л)"
        tank_cost = 24000
    else:
        tank_spec = f"Гидроаккумулятор 200-300 л (для {houses} домов)"
        tank_cost = 38000

    # 4. Труба, кабель и трос (метраж с запасом 15%)
    pipe_downhole_m = int(pump_depth * 1.1)
    cable_downhole_m = int((pump_depth + 5) * 1.1)
    cable_trench_m = int(distance * 1.05)
    rope_stainless_m = int(pump_depth + 6)

    # 5. Смета материалов
    # Труба ПНД 32 SDR11 (110 руб/м), трос 4мм нерж (130 руб/м), кабель КВВ-П (160 руб/м)
    downhole_materials = (pipe_downhole_m * 110) + (rope_stainless_m * 130) + (cable_downhole_m * 160) + 9500  # оголовок, клапан, зажимы
    
    # Трасса: земляные работы + труба в утеплителе (1200 руб/м)
    total_trench_distance = distance * houses
    trench_cost = int(total_trench_distance * 1200)

    # Кессон (для 1 дома стандарт, для 2-3 домов с увеличенной рабочей частью под гребёнку)
    if houses == 1:
        kesson_name = "Кессон пластиковый «МИШКА-2» с муфтой"
        kesson_cost = 48000
    else:
        kesson_name = "Кессон пластиковый «МИШКА-3» (увеличенный под гребёнку)"
        kesson_cost = 58000

    automation_kit_cost = tank_cost + 9000  # реле, пятерник, манометр, фильтр BB10
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

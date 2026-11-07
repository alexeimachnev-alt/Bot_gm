import os
from telebot import types

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "551209811"))

user_calc_sessions = {}

# Каталог доп. расходников с переводом на 5 языков
EXTRA_ITEMS = {
    "pnd32": {
        "unit_type": "meters",
        "ru_unit": "м",
        "names": {
            "ru": "Труба ПНД 32 SDR11",
            "tj": "Қубури ПНД 32 SDR11",
            "uz": "PND 32 trubasi SDR11",
            "hy": "Խողովակ ՊՆԴ 32 SDR11",
            "ky": "ПНД 32 түтүгү SDR11"
        }
    },
    "pnd25": {
        "unit_type": "meters",
        "ru_unit": "м",
        "names": {
            "ru": "Труба ПНД 25 (полив)",
            "tj": "Қубури ПНД 25 (обёрӣ)",
            "uz": "PND 25 trubasi (sug'orish)",
            "hy": "Խողովակ ՊՆԴ 25 (ոռոգում)",
            "ky": "ПНД 25 түтүгү (сугаруу)"
        }
    },
    "insul": {
        "unit_type": "meters",
        "ru_unit": "м",
        "names": {
            "ru": "Утеплитель Энергофлекс 32",
            "tj": "Гармидиҳандаи Энергофлекс 32",
            "uz": "Energofleks izolyatsiyasi 32",
            "hy": "Ջերմամեկուսիչ Էներգոֆլեքս 32",
            "ky": "Энергофлекс жылуулагычы 32"
        }
    },
    "heat_cable": {
        "unit_type": "meters",
        "ru_unit": "м",
        "names": {
            "ru": "Кабель греющий саморег.",
            "tj": "Кабели гармкунанда",
            "uz": "Isitish kabeli",
            "hy": "Տաքացնող մալուխ",
            "ky": "Жылытуучу кабель"
        }
    },
    "ball_valve": {
        "unit_type": "pieces",
        "ru_unit": "шт.",
        "names": {
            "ru": "Кран 1\" с американкой",
            "tj": "Крани 1\" бо американка",
            "uz": "Kran 1\" amerikanka bilan",
            "hy": "Ծորակ 1\" ամերիկանկայով",
            "ky": "Кран 1\" американка менен"
        }
    },
    "fitting_32_1": {
        "unit_type": "pieces",
        "ru_unit": "шт.",
        "names": {
            "ru": "Муфта ПНД 32х1\" НР",
            "tj": "Муфтаи ПНД 32х1\" БО",
            "uz": "Mufta PND 32x1\" TQ",
            "hy": "Կցորդիչ ՊՆԴ 32х1\" ԱՊ",
            "ky": "Муфта ПНД 32х1\" СТ"
        }
    },
    "elbow_32": {
        "unit_type": "pieces",
        "ru_unit": "шт.",
        "names": {
            "ru": "Уголок ПНД 32х32 (90°)",
            "tj": "Кунҷак (угловой) ПНД 32х32",
            "uz": "Tirsak PND 32x32 (90°)",
            "hy": "Անկյունակ ՊՆԴ 32х32",
            "ky": "Бурчтук ПНД 32х32"
        }
    },
    "unipak": {
        "unit_type": "pieces",
        "ru_unit": "шт.",
        "names": {
            "ru": "Лён + паста Unipak",
            "tj": "Зиғирпоя (лён) + хамираи Unipak",
            "uz": "Zig'ir tolasi (lyon) + Unipak pasta",
            "hy": "Վուշաթել (լյոն) + մածուկ Unipak",
            "ky": "Зыгыр буласы (лен) + Unipak пастасы"
        }
    }
}

# Данные официального прайса «МИШКА»
PRICE_DATA = {
    "m1": (
        "🐻 <b>КЕССОНЫ МИШКА 1 (Ø1050 мм)</b>\n"
        "<i>Материал: первичный монолитный полипропилен</i>\n\n"
        "🔹 <b>Мишка 1 (H=2000 мм):</b>\n"
        "• Проходной (без фланца): ОПТ <b>36 650 ₽</b> | МРЦ 58 000 ₽\n"
        "• Фланец 125/133 мм: ОПТ <b>39 650 ₽</b> | МРЦ 61 000 ₽\n"
        "• Фланец 159 мм: ОПТ <b>42 650 ₽</b> | МРЦ 64 000 ₽\n\n"
        "🔹 <b>Мишка 1 LONG (H=2500 мм):</b>\n"
        "• Проходной (без фланца): ОПТ <b>49 650 ₽</b> | МРЦ 78 000 ₽\n"
        "• Фланец 125/133 мм: ОПТ <b>52 650 ₽</b> | МРЦ 81 000 ₽\n"
        "• Фланец 159 мм: ОПТ <b>56 650 ₽</b> | МРЦ 85 000 ₽\n\n"
        "<i>* Сгоны d32 мм (комплект 4 шт.): +1 520 ₽</i>"
    ),
    "m2": (
        "🐻 <b>КЕССОНЫ МИШКА 2 (Ø1300 мм)</b>\n"
        "<i>Материал: первичный монолитный полипропилен</i>\n\n"
        "🔹 <b>Мишка 2 (H=2000 мм):</b>\n"
        "• Проходной (без фланца): ОПТ <b>47 700 ₽</b> | МРЦ 75 000 ₽\n"
        "• Фланец 125/133 мм: ОПТ <b>50 700 ₽</b> | МРЦ 78 000 ₽\n"
        "• Фланец 159 мм: ОПТ <b>53 300 ₽</b> | МРЦ 82 000 ₽\n\n"
        "🔹 <b>Мишка 2 LONG (H=2500 мм):</b>\n"
        "• Проходной (без фланца): ОПТ <b>57 800 ₽</b> | МРЦ 89 000 ₽\n"
        "• Фланец 125/133 мм: ОПТ <b>65 000 ₽</b> | МРЦ 95 000 ₽\n"
        "• Фланец 159 мм: ОПТ <b>68 800 ₽</b> | МРЦ 100 000 ₽\n\n"
        "<i>* Сгоны d32 мм (комплект 4 шт.): +1 520 ₽</i>"
    ),
    "m3": (
        "🐻 <b>КЕССОНЫ МИШКА 3 (Ø1600 мм)</b>\n"
        "<i>Материал: первичный монолитный полипропилен</i>\n\n"
        "🔹 <b>Мишка 3 (H=2000 мм):</b>\n"
        "• Проходной (без фланца): ОПТ <b>70 000 ₽</b> | МРЦ 101 000 ₽\n"
        "• Фланец 125/133 мм: ОПТ <b>76 500 ₽</b> | МРЦ 115 000 ₽\n"
        "• Фланец 159 мм: ОПТ <b>81 300 ₽</b> | МРЦ 124 600 ₽\n\n"
        "🔹 <b>Мишка 3 LONG (H=2500 мм):</b>\n"
        "• Проходной (без фланца): ОПТ <b>113 200 ₽</b> | МРЦ 154 300 ₽\n"
        "• Фланец 125/133 мм: ОПТ <b>118 300 ₽</b> | МРЦ 161 200 ₽\n"
        "• Фланец 159 мм: ОПТ <b>124 200 ₽</b> | МРЦ 166 100 ₽\n\n"
        "<i>* Сгоны d32 мм (комплект 4 шт.): +1 520 ₽</i>"
    ),
    "m4": (
        "🐻 <b>КЕССОНЫ МИШКА 4 (Ø2100 мм)</b>\n"
        "<i>Материал: первичный монолитный полипропилен</i>\n\n"
        "🔹 <b>Мишка 4 (H=2000 мм):</b>\n"
        "• Проходной (без фланца): ОПТ <b>145 900 ₽</b> | РРЦ 191 600 ₽\n"
        "• Фланец 125/133 мм: ОПТ <b>156 000 ₽</b> | РРЦ 194 600 ₽\n"
        "• Фланец 159 мм: ОПТ <b>164 111 ₽</b> | РРЦ 199 600 ₽\n\n"
        "🔹 <b>Мишка 4 LONG (H=2500 мм):</b>\n"
        "• Проходной (без фланца): ОПТ <b>199 000 ₽</b> | РРЦ 245 600 ₽\n"
        "• Фланец 125/133 мм: ОПТ <b>204 050 ₽</b> | РРЦ 250 600 ₽\n"
        "• Фланец 159 мм: ОПТ <b>213 000 ₽</b> | РРЦ 287 400 ₽\n\n"
        "<i>* Сгоны d32 мм (комплект 4 шт.): +1 520 ₽</i>"
    ),
    "rings": (
        "🧱 <b>ГЕРМЕТИЧНЫЕ ВСТАВКИ В Ж/Б КОЛОДЦЫ</b>\n"
        "<i>Пластиковые вставки (D = диаметр, H = высота):</i>\n\n"
        "🔹 <b>Диаметр 0.9 м (D=0.9):</b>\n"
        "• H=0.9 м: ОПТ <b>18 750 ₽</b> | Розница 25 000 ₽\n"
        "• H=1.8 м: ОПТ <b>33 750 ₽</b> | Розница 45 000 ₽\n"
        "• H=2.7 м: ОПТ <b>40 213 ₽</b> | Розница 53 100 ₽\n"
        "• H=3.6 м: ОПТ <b>55 738 ₽</b> | Розница 78 000 ₽\n"
        "• H=4.5 м: ОПТ <b>80 500 ₽</b> | Розница 106 000 ₽\n"
        "• H=5.4 м: ОПТ <b>96 875 ₽</b> | Розница 129 000 ₽\n\n"
        "🔹 <b>Диаметр 1.4 м (D=1.4):</b>\n"
        "• H=0.9 м: ОПТ <b>27 738 ₽</b> | Розница 48 000 ₽\n"
        "• H=1.8 м: ОПТ <b>42 875 ₽</b> | Розница 56 000 ₽\n"
        "• H=2.7 м: ОПТ <b>51 713 ₽</b> | Розница 78 000 ₽\n"
        "• H=3.6 м: ОПТ <b>72 100 ₽</b> | Розница 99 000 ₽\n"
        "• H=4.5 м: ОПТ <b>85 400 ₽</b> | Розница 122 000 ₽\n"
        "• H=5.4 м: ОПТ <b>112 875 ₽</b> | Розница 132 000 ₽\n\n"
        "🔹 <b>Диаметр 1.8 м (D=1.8):</b>\n"
        "• H=0.9 м: ОПТ <b>45 000 ₽</b> | Розница 60 000 ₽\n"
        "• H=1.8 м: ОПТ <b>60 000 ₽</b> | Розница 80 000 ₽\n"
        "• H=2.7 м: ОПТ <b>80 000 ₽</b> | Розница 100 000 ₽\n"
        "• H=3.6 м: ОПТ <b>100 000 ₽</b> | Розница 120 000 ₽\n"
        "• H=4.5 м: ОПТ <b>119 000 ₽</b> | Розница 140 000 ₽\n"
        "• H=5.4 м: ОПТ <b>135 000 ₽</b> | Розница 167 000 ₽"
    )
}

# Тексты интерфейса опроса
LANG_TEXTS = {
    "ru": {
        "lang_name": "Русский",
        "intro": "🔧 <b>Параметры скважины для выдачи комплекта:</b>\n\n1️⃣ <b>Глубина скважины (в метрах):</b>\n<i>(введите число, например: 40)</i>",
        "err_depth": "⚠️ Введите глубину числом (например: 40):",
        "q_yield": "2️⃣ <b>Дебит (производительность) скважины в м³/час:</b>\n<i>(по паспорту, либо в среднем: 2 или 3)</i>",
        "err_yield": "⚠️ Введите дебит числом (например: 2.5):",
        "q_houses": "3️⃣ <b>Сколько строений (домов) подключаем?</b>\n<i>(введите число, например: 1 или 2)</i>",
        "err_houses": "⚠️ Введите количество домов целым числом (например: 1):",
        "q_dist_single": "4️⃣ <b>Расстояние от скважины до дома (в метрах):</b>\n<i>(например: 15)</i>",
        "q_dist_first": "4️⃣ <b>Расстояние от скважины до Дома №1 (в метрах):</b>\n<i>(например: 15)</i>",
        "q_dist_next": "▫️ <b>Расстояние от скважины до Дома №{idx} (в метрах):</b>\n<i>(например: 25)</i>",
        "err_dist": "⚠️ Введите расстояние числом метров (например: 15):",
        "extras_title": "📦 <b>Нужны ли дополнительные расходные материалы с собой?</b>\nВыберите позиции кнопками ниже (нажмите «Готово», когда выберете всё необходимое):",
        "ask_meters": "📏 Введите количество в <b>метрах</b> для «{name}» (например: 20):",
        "ask_pieces": "🔢 Введите количество в <b>штуках</b> для «{name}» (например: 3):",
        "err_qty": "⚠️ Введите положительное число:",
        "unit_m": "м",
        "unit_pcs": "шт.",
        "btn_done": "✅ Готово / Завершить заказ",
        "done": "✅ <b>Спасибо! Запрос принят.</b>\nСпецификация и доп. материалы переданы на склад, комплектуем заказ к вашему приезду."
    },
    "tj": {
        "lang_name": "Тоҷикӣ",
        "intro": "🔧 <b>Параметрҳои чоҳ барои гирифтани маҷмӯа:</b>\n\n1️⃣ <b>Чуқурии чоҳ (бо метр):</b>\n<i>(рақам нависед, масалан: 40)</i>",
        "err_depth": "⚠️ Лутфан чуқуриро бо рақам нависед (масалан: 40):",
        "q_yield": "2️⃣ <b>Дебити (ҳосилнокии) чоҳ бо м³/соат:</b>\n<i>(аз рӯи шиноснома, ё ба ҳисоби миёна: 2 ё 3)</i>",
        "err_yield": "⚠️ Ҳосилнокиро бо рақам нависед (масалан: 2.5):",
        "q_houses": "3️⃣ <b>Чанд хонаро васл кардан лозим аст?</b>\n<i>(рақам нависед, масалан: 1 ё 2)</i>",
        "err_houses": "⚠️ Шумораи хонаҳоро бо рақами бутун нависед (масалан: 1):",
        "q_dist_single": "4️⃣ <b>Масофа аз чоҳ то хона (бо метр):</b>\n<i>(масалан: 15)</i>",
        "q_dist_first": "4️⃣ <b>Масофа аз чоҳ то Хонаи №1 (бо метр):</b>\n<i>(масалан: 15)</i>",
        "q_dist_next": "▫️ <b>Масофа аз чоҳ то Хонаи №{idx} (бо метр):</b>\n<i>(масалан: 25)</i>",
        "err_dist": "⚠️ Масофаро бо рақам нависед (масалан: 15):",
        "extras_title": "📦 <b>Оё маводи иловагӣ лозим аст?</b>\nАз тугмаҳои зерин интихоб кунед (баъди тамом кардан тугмаи «Тайёр»-ро пахш кунед):",
        "ask_meters": "📏 Миқдорро бо <b>метр</b> барои «{name}» нависед (масалан: 20):",
        "ask_pieces": "🔢 Миқдорро бо <b>дона (шт)</b> барои «{name}» нависед (масалан: 3):",
        "err_qty": "⚠️ Рақами дурустро нависед:",
        "unit_m": "м",
        "unit_pcs": "дона",
        "btn_done": "✅ Тайёр / Фиристодани фармоиш",
        "done": "✅ <b>Ташаккур! Дархости шумо қабул шуд.</b>\nМаълумот ва маводи иловагӣ ба анбор супорида шуд, мо борро тайёр мекунем."
    },
    "uz": {
        "lang_name": "Oʻzbekcha",
        "intro": "🔧 <b>Komplektni olish uchun quduq parametrlari:</b>\n\n1️⃣ <b>Quduq chuqurligi (metrda):</b>\n<i>(faqat raqam kiriting, masalan: 40)</i>",
        "err_depth": "⚠️ Iltimos chuqurlikni raqamda kiriting (masalan: 40):",
        "q_yield": "2️⃣ <b>Quduq suv berish quvvati (debit) m³/soat:</b>\n<i>(pasport bo'yicha yoki o'rtacha: 2 yoki 3)</i>",
        "err_yield": "⚠️ Quvvatni raqamda kiriting (masalan: 2.5):",
        "q_houses": "3️⃣ <b>Nechta uyga suv ulanadi?</b>\n<i>(faqat raqam kiriting, masalan: 1 yoki 2)</i>",
        "err_houses": "⚠️ Uylar sonini butun raqamda kiriting (masalan: 1):",
        "q_dist_single": "4️⃣ <b>Quduqdan uygacha bo'lgan masofa (metrda):</b>\n<i>(masalan: 15)</i>",
        "q_dist_first": "4️⃣ <b>Quduqdan 1-raqamli uygacha masofa (metrda):</b>\n<i>(masalan: 15)</i>",
        "q_dist_next": "▫️ <b>Quduqdan {idx}-raqamli uygacha masofa (metrda):</b>\n<i>(masalan: 25)</i>",
        "err_dist": "⚠️ Masofani raqamda kiriting (masalan: 15):",
        "extras_title": "📦 <b>Qo'shimcha sarflanuvchi materiallar kerakmi?</b>\nKerakli mahsulotlarni tugmalar orqali tanlang (tugatgach «Tayyor» tugmasini bosing):",
        "ask_meters": "📏 «{name}» uchun miqdorni <b>metrda</b> kiriting (masalan: 20):",
        "ask_pieces": "🔢 «{name}» uchun miqdorni <b>donada</b> kiriting (masalan: 3):",
        "err_qty": "⚠️ To'g'ri raqam kiriting:",
        "unit_m": "m",
        "unit_pcs": "dona",
        "btn_done": "✅ Tayyor / Buyurtmani yuborish",
        "done": "✅ <b>Rahmat! Buyurtmangiz qabul qilindi.</b>\nMaʼlumot omborga yuborildi, yetib kelishingizga mahsulotlarni yigʻishni boshladik."
    },
    "hy": {
        "lang_name": "Հայերեն",
        "intro": "🔧 <b>Հորատանցքի տվյալները հավաքածուն ստանալու համար:</b>\n\n1️⃣ <b>Հորատանցքի խորությունը (մետրերով):</b>\n<i>(գրեք թիվ, օրինակ՝ 40)</i>",
        "err_depth": "⚠️ Խնդրում ենք խորությունը գրել թվով (օրինակ՝ 40):",
        "q_yield": "2️⃣ <b>Հորատանցքի արտադրողականությունը (մ³/ժամ):</b>\n<i>(ըստ անձնագրի, կամ միջինը՝ 2 կամ 3)</i>",
        "err_yield": "⚠️ Արտադրողականությունը գրեք թվով (օրինակ՝ 2.5):",
        "q_houses": "3️⃣ <b>Քանի՞ տուն պետք է միացնել:</b>\n<i>(գրեք թիվ, օրինակ՝ 1 կամ 2)</i>",
        "err_houses": "⚠️ Տների քանակը գրեք ամբողջ թվով (օրինակ՝ 1):",
        "q_dist_single": "4️⃣ <b>Հեռավորությունը հորատանցքից մինչև տուն (մետրերով):</b>\n<i>(օրինակ՝ 15)</i>",
        "q_dist_first": "4️⃣ <b>Հեռավորությունը հորատանցքից մինչև Տուն №1 (մետրերով):</b>\n<i>(օրինակ՝ 15)</i>",
        "q_dist_next": "▫️ <b>Հեռավորությունը հորատանցքից մինչև Տուն №{idx} (մետրերով):</b>\n<i>(օրինակ՝ 25)</i>",
        "err_dist": "⚠️ Հեռավորությունը գրեք թվով (օրինակ՝ 15):",
        "extras_title": "📦 <b>Լրացուցիչ նյութեր անհրաժե՞շտ են:</b>\nԸնտրեք անհրաժեշտ ապրանքները (ավարտելուց հետո սեղմեք «Պատրաստ է»):",
        "ask_meters": "📏 Գրեք քանակը <b>մետրերով</b> «{name}» համար (օրինակ՝ 20):",
        "ask_pieces": "🔢 Գրեք քանակը <b>հատերով</b> «{name}» համար (օրինակ՝ 3):",
        "err_qty": "⚠️ Գրեք ճիշտ թիվ:",
        "unit_m": "մ",
        "unit_pcs": "հատ",
        "btn_done": "✅ Պատրաստ է / Ուղարկել",
        "done": "✅ <b>Շնորհակալություն: Ձեր հարցումն ընդունված է:</b>\nՏվյալները փոխանցվել են պահեստ, սկսում ենք ապրանքի հավաքումը:"
    },
    "ky": {
        "lang_name": "Кыргызча",
        "intro": "🔧 <b>Комплектти алуу үчүн скважинанын параметрлери:</b>\n\n1️⃣ <b>Скважинанын тереңдиги (метр менен):</b>\n<i>(сан жазыңыз, мисалы: 40)</i>",
        "err_depth": "⚠️ Тереңдикти сан менен жазыңыз (мисалы: 40):",
        "q_yield": "2️⃣ <b>Скважинанын суу берүү кубаттуулугу (м³/саат):</b>\n<i>(паспорт боюнча, же орточо: 2 же 3)</i>",
        "err_yield": "⚠️ Кубаттуулукту сан менен жазыңыз (мисалы: 2.5):",
        "q_houses": "3️⃣ <b>Канча үйгө суу туташтырылат?</b>\n<i>(сан жазыңыз, мисалы: 1 же 2)</i>",
        "err_houses": "⚠️ Үйлөрдүн санын бүтүн сан менен жазыңыз (мисалы: 1):",
        "q_dist_single": "4️⃣ <b>Скважинадан үйгө чейинки аралык (метр менен):</b>\n<i>(мисалы: 15)</i>",
        "q_dist_first": "4️⃣ <b>Скважинадан №1 үйгө чейинки аралык (метр менен):</b>\n<i>(мисалы: 15)</i>",
        "q_dist_next": "▫️ <b>Скважинадан №{idx} үйгө чейинки аралык (метр менен):</b>\n<i>(мисалы: 25)</i>",
        "err_dist": "⚠️ Аралыкты сан менен жазыңыз (мисалы: 15):",
        "extras_title": "📦 <b>Кошумча керектелүүчү материалдар керекпи?</b>\nТөмөнкү баскычтардан тандаңыз (бүткөндөн кийин «Даяр» баскычын басыңыз):",
        "ask_meters": "📏 «{name}» үчүн өлчөмдү <b>метр</b> менен жазыңыз (мисалы: 20):",
        "ask_pieces": "🔢 «{name}» үчүн санын <b>даана (шт)</b> менен жазыңыз (мисалы: 3):",
        "err_qty": "⚠️ Туура санды жазыңыз:",
        "unit_m": "м",
        "unit_pcs": "даана",
        "btn_done": "✅ Даяр / Буйрутманы жөнөтүү",
        "done": "✅ <b>Ырахмат! Суроо-талап кабыл алынды.</b>\nМаалымат кампага жөнөтүлдү, сиз келгенче жүктү топтой баштайбыз."
    }
}


def build_warehouse_checklist(data: dict) -> str:
    """Формирует сборочный лист склада строго на русском языке."""
    depth = data["depth"]
    yield_flow = data["yield_flow"]
    houses = data["houses"]
    distances = data["distances"]
    extras = data.get("extras", {})
    user_lang = LANG_TEXTS.get(data.get("lang", "ru"), {}).get("lang_name", "Русский")

    total_distance = sum(distances)
    max_distance = max(distances)

    pump_depth = max(10, int(depth - 5))
    total_pipe_run = pump_depth + max_distance
    friction_losses = total_pipe_run * 0.10
    required_head = int(pump_depth + friction_losses + 30 + 5)

    if required_head <= 60:
        pump_model = "Насос скважинный 3\"/4\" (напор 60-70 м, 2.5-3.0 м³/ч)"
    elif required_head <= 85:
        pump_model = "Насос скважинный 3\"/4\" (напор 80-90 м, 3.0-3.5 м³/ч)"
    elif required_head <= 110:
        pump_model = "Насос скважинный усиленный (напор 100-115 м)"
    else:
        pump_model = "Насос высоконапорный промышленной серии (напор 120+ м)"

    if houses == 1:
        kesson_name = "Кессон пластиковый «МИШКА-2» (1000х2000 мм)"
        branch_tees = 1
    else:
        kesson_name = f"Кессон пластиковый «МИШКА-3» (увеличенный с гребёнкой на {houses} вывода)"
        branch_tees = houses

    if houses == 1:
        tank_spec = "Гидроаккумулятор 80-100 л (вертикальный, фланец нерж)"
    elif houses == 2:
        tank_spec = "Гидроаккумулятор 150 л (или 2 шт. по 80-100 л)"
    else:
        tank_spec = f"Гидроаккумулятор 200-300 л (под {houses} домов)"

    pnd_downhole = int(pump_depth * 1.05)
    pnd_trench = int(total_distance * 1.05)
    total_pnd_pipe = pnd_downhole + pnd_trench + (houses * 4)
    cable_m = int((pump_depth + 5) * 1.1)
    rope_m = int(pump_depth + 6)
    cable_ties = max(40, int(pump_depth * 1.5))
    insulation_m = int(total_distance + (houses * 2))

    if houses == 1:
        routes_detail = f"• Трасса до дома: <b>{distances[0]} м</b>\n"
    else:
        routes_detail = f"• Домов: <b>{houses} шт.</b> (общая длина трасс: <b>{total_distance} м</b>):\n"
        for idx, d in enumerate(distances, start=1):
            routes_detail += f"   ▫️ Дом №{idx}: <b>{d} м</b>\n"

    extras_block = ""
    if extras:
        extras_block = "\n🔥 <b>ДОПОЛНИТЕЛЬНЫЕ РАСХОДНИКИ (ПО ЗАПРОСУ МОНТАЖНИКА):</b>\n"
        for item_key, qty in extras.items():
            item_info = EXTRA_ITEMS.get(item_key)
            if item_info:
                ru_title = item_info["names"]["ru"]
                u_str = item_info["ru_unit"]
                extras_block += f"  ➕ <b>{ru_title}</b> — <b>{qty} {u_str}</b>\n"
    else:
        extras_block = "\n▫️ <i>Дополнительных расходников не запрошено.</i>\n"

    checklist = (
        f"📦 <b>ЗАКАЗ НА СКЛАДСКУЮ СБОРКУ КОМПЛЕКТА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👷 <b>Монтажник:</b> {data['worker_name']} ({data['worker_tag']})\n"
        f"🌐 <b>Язык заполнения:</b> {user_lang}\n"
        f"🆔 ID чата: <code>{data['chat_id']}</code>\n\n"
        f"📋 <b>Входные параметры объекта:</b>\n"
        f"• Глубина скважины: <b>{depth} м</b> (подвеска насоса на ~{pump_depth} м)\n"
        f"• Дебит: <b>{yield_flow} м³/ч</b> | Расчётный напор: <b>{required_head} м</b>\n"
        f"{routes_detail}\n"
        f"🛠 <b>ОСНОВНОЙ КОМПЛЕКТ НА ОТГРУЗКУ:</b>\n\n"
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
        f"{extras_block}"
    )
    return checklist


def get_language_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    b_price = types.InlineKeyboardButton("🏷 Прайс КЕССОН МИШКА", callback_data="price_back_main")
    b_ru = types.InlineKeyboardButton("🇷🇺 Русский", callback_data="calc_lang_ru")
    b_tj = types.InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="calc_lang_tj")
    b_uz = types.InlineKeyboardButton("🇺🇿 Oʻzbekcha", callback_data="calc_lang_uz")
    b_hy = types.InlineKeyboardButton("🇦🇲 Հայերեն", callback_data="calc_lang_hy")
    b_ky = types.InlineKeyboardButton("🇰🇬 Кыргызча", callback_data="calc_lang_ky")
    keyboard.add(b_price)
    keyboard.add(b_ru)
    keyboard.add(b_tj, b_uz)
    keyboard.add(b_hy, b_ky)
    return keyboard


def get_price_categories_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("🐻 Мишка 1 (Ø1050)", callback_data="price_view_m1")
    b2 = types.InlineKeyboardButton("🐻 Мишка 2 (Ø1300)", callback_data="price_view_m2")
    b3 = types.InlineKeyboardButton("🐻 Мишка 3 (Ø1600)", callback_data="price_view_m3")
    b4 = types.InlineKeyboardButton("🐻 Мишка 4 (Ø2100)", callback_data="price_view_m4")
    b5 = types.InlineKeyboardButton("🧱 Вставки в ж/б колодцы", callback_data="price_view_rings")
    kb.add(b1, b2)
    kb.add(b3, b4)
    kb.add(b5)
    return kb


def get_extras_keyboard(chat_id, lang):
    t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
    session = user_calc_sessions.get(chat_id, {})
    extras = session.get("extras", {})

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for key, item in EXTRA_ITEMS.items():
        name = item["names"].get(lang, item["names"]["ru"])
        qty = extras.get(key)
        u_label = t["unit_m"] if item["unit_type"] == "meters" else t["unit_pcs"]
        mark = f" ✅ ({qty} {u_label})" if qty else ""
        btn_text = f"{name}{mark}"
        buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"extra_pick_{key}"))

    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.add(buttons[i], buttons[i+1])
        else:
            keyboard.add(buttons[i])

    keyboard.add(types.InlineKeyboardButton(t["btn_done"], callback_data="extra_finish"))
    return keyboard


def register_calc_handlers(bot):

    # 1. Команда просмотра прайс-листа
    @bot.message_handler(commands=['price', 'прайс'])
    def handle_price_cmd(message):
        bot.reply_to(
            message,
            "🏷 <b>Официальный прайс-лист продукции «МИШКА»:</b>\n\n"
            "Выберите интересующую категорию кессонов или вставок:",
            reply_markup=get_price_categories_keyboard(),
            parse_mode="HTML"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("price_view_"))
    def handle_price_view(call):
        cat = call.data.replace("price_view_", "")
        bot.answer_callback_query(call.id)
        text = PRICE_DATA.get(cat, "Раздел не найден.")
        back_kb = types.InlineKeyboardMarkup()
        back_kb.add(types.InlineKeyboardButton("⬅️ Назад ко всем моделям", callback_data="price_back_main"))
        bot.send_message(call.message.chat.id, text, reply_markup=back_kb, parse_mode="HTML")

    @bot.callback_query_handler(func=lambda call: call.data == "price_back_main")
    def handle_price_back(call):
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "🏷 <b>Прайс-лист «МИШКА»:</b>\nВыберите модель:",
            reply_markup=get_price_categories_keyboard(),
            parse_mode="HTML"
        )

    # 2. Калькулятор и сборка заказа
    @bot.message_handler(commands=['calc', 'smeta'])
    def start_calc(message):
        bot.reply_to(
            message,
            "🌐 <b>Выберите язык / Забонро интихоб кунед / Tilni tanlang / Ընտրեք լեզուն / Тилди тандаңыз:</b>",
            reply_markup=get_language_keyboard(),
            parse_mode="HTML"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("calc_lang_"))
    def handle_language_choice(call):
        chosen_lang = call.data.replace("calc_lang_", "")
        chat_id = call.message.chat.id

        user_calc_sessions[chat_id] = {
            "lang": chosen_lang,
            "distances": [],
            "extras": {}
        }

        bot.answer_callback_query(call.id)
        t = LANG_TEXTS.get(chosen_lang, LANG_TEXTS["ru"])

        bot.send_message(chat_id, t["intro"], parse_mode="HTML")
        bot.register_next_step_handler(call.message, lambda m: step_depth(m, bot, chosen_lang))

    def step_depth(message, bot, lang):
        if message.text and message.text.startswith('/'):
            return
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
        try:
            val = float(message.text.replace(",", "."))
            if val <= 0 or val > 300:
                raise ValueError
            user_calc_sessions[message.chat.id]["depth"] = val
            bot.reply_to(message, t["q_yield"], parse_mode="HTML")
            bot.register_next_step_handler(message, lambda m: step_yield(m, bot, lang))
        except (ValueError, TypeError):
            bot.reply_to(message, t["err_depth"])
            bot.register_next_step_handler(message, lambda m: step_depth(m, bot, lang))

    def step_yield(message, bot, lang):
        if message.text and message.text.startswith('/'):
            return
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
        try:
            val = float(message.text.replace(",", "."))
            if val <= 0 or val > 50:
                raise ValueError
            user_calc_sessions[message.chat.id]["yield_flow"] = val
            bot.reply_to(message, t["q_houses"], parse_mode="HTML")
            bot.register_next_step_handler(message, lambda m: step_houses(m, bot, lang))
        except (ValueError, TypeError):
            bot.reply_to(message, t["err_yield"])
            bot.register_next_step_handler(message, lambda m: step_yield(m, bot, lang))

    def step_houses(message, bot, lang):
        if message.text and message.text.startswith('/'):
            return
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
        try:
            val = int(message.text.strip())
            if val < 1 or val > 10:
                raise ValueError
            user_calc_sessions[message.chat.id]["houses"] = val
            user_calc_sessions[message.chat.id]["distances"] = []

            if val == 1:
                bot.reply_to(message, t["q_dist_single"], parse_mode="HTML")
                bot.register_next_step_handler(message, lambda m: step_single_distance(m, bot, lang))
            else:
                bot.reply_to(message, t["q_dist_first"], parse_mode="HTML")
                bot.register_next_step_handler(message, lambda m: step_multi_distance(m, bot, lang, house_idx=1))
        except (ValueError, TypeError):
            bot.reply_to(message, t["err_houses"])
            bot.register_next_step_handler(message, lambda m: step_houses(m, bot, lang))

    def step_single_distance(message, bot, lang):
        if message.text and message.text.startswith('/'):
            return
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
        try:
            val = float(message.text.replace(",", "."))
            if val < 0 or val > 1000:
                raise ValueError
            user_calc_sessions[message.chat.id]["distances"] = [val]
            show_extras_menu(message.chat.id, bot, lang)
        except (ValueError, TypeError):
            bot.reply_to(message, t["err_dist"])
            bot.register_next_step_handler(message, lambda m: step_single_distance(m, bot, lang))

    def step_multi_distance(message, bot, lang, house_idx):
        if message.text and message.text.startswith('/'):
            return
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
        try:
            val = float(message.text.replace(",", "."))
            if val < 0 or val > 1000:
                raise ValueError

            user_calc_sessions[message.chat.id]["distances"].append(val)
            total_houses = user_calc_sessions[message.chat.id]["houses"]

            if house_idx < total_houses:
                next_house = house_idx + 1
                q_text = t["q_dist_next"].format(idx=next_house)
                bot.reply_to(message, q_text, parse_mode="HTML")
                bot.register_next_step_handler(message, lambda m: step_multi_distance(m, bot, lang, house_idx=next_house))
            else:
                show_extras_menu(message.chat.id, bot, lang)
        except (ValueError, TypeError):
            bot.reply_to(message, t["err_dist"])
            bot.register_next_step_handler(message, lambda m: step_multi_distance(m, bot, lang, house_idx=house_idx))

    def show_extras_menu(chat_id, bot, lang):
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
        markup = get_extras_keyboard(chat_id, lang)
        bot.send_message(chat_id, t["extras_title"], reply_markup=markup, parse_mode="HTML")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("extra_pick_"))
    def handle_extra_pick(call):
        item_key = call.data.replace("extra_pick_", "")
        chat_id = call.message.chat.id
        session = user_calc_sessions.get(chat_id, {})
        lang = session.get("lang", "ru")
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
        item = EXTRA_ITEMS.get(item_key)

        if not item:
            bot.answer_callback_query(call.id)
            return

        bot.answer_callback_query(call.id)
        local_name = item["names"].get(lang, item["names"]["ru"])

        if item["unit_type"] == "meters":
            msg_text = t["ask_meters"].format(name=local_name)
        else:
            msg_text = t["ask_pieces"].format(name=local_name)

        bot.send_message(chat_id, msg_text, parse_mode="HTML")
        bot.register_next_step_handler(call.message, lambda m: save_extra_quantity(m, bot, item_key, lang))

    def save_extra_quantity(message, bot, item_key, lang):
        if message.text and message.text.startswith('/'):
            return
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])
        try:
            raw_val = message.text.replace(",", ".").strip()
            qty = float(raw_val) if "." in raw_val else int(raw_val)
            if qty <= 0:
                raise ValueError

            if "extras" not in user_calc_sessions[message.chat.id]:
                user_calc_sessions[message.chat.id]["extras"] = {}
            user_calc_sessions[message.chat.id]["extras"][item_key] = qty

            show_extras_menu(message.chat.id, bot, lang)
        except (ValueError, TypeError):
            bot.reply_to(message, t["err_qty"])
            bot.register_next_step_handler(message, lambda m: save_extra_quantity(m, bot, item_key, lang))

    @bot.callback_query_handler(func=lambda call: call.data == "extra_finish")
    def handle_extra_finish(call):
        chat_id = call.message.chat.id
        session = user_calc_sessions.get(chat_id, {})
        lang = session.get("lang", "ru")
        t = LANG_TEXTS.get(lang, LANG_TEXTS["ru"])

        bot.answer_callback_query(call.id)

        session["worker_tag"] = f"@{call.from_user.username}" if call.from_user.username else "нет username"
        session["worker_name"] = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip() or "Монтажник"
        session["chat_id"] = chat_id

        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

        bot.send_message(chat_id, t["done"], parse_mode="HTML")

        checklist = build_warehouse_checklist(session)
        try:
            bot.send_message(ADMIN_CHAT_ID, checklist, parse_mode="HTML")
            print(f"[SUCCESS] Сборочный лист отправлен админу {ADMIN_CHAT_ID}")
        except Exception as e:
            print(f"[ERROR] Ошибка отправки админу {ADMIN_CHAT_ID}: {e}")

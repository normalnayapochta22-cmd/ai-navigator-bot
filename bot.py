import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from yookassa import Configuration, Payment
from database import Database
import config

# Настройка ЮKassa
Configuration.account_id = config.YUKASSA_SHOP_ID
Configuration.secret_key = config.YUKASSA_SECRET_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
db = Database()


# Состояния для FSM
class AdminMessage(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_message = State()


class AdminBroadcast(StatesGroup):
    waiting_for_broadcast_message = State()


# Клавиатуры
def get_main_keyboard():
    """Главное меню - inline кнопки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Информация о клубе", callback_data="info_club")],
            [InlineKeyboardButton(text="📚 Программа курса", callback_data="program")],
            [InlineKeyboardButton(text="💳 Оплатить доступ", callback_data="payment_start")],
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton(text="💬 Задать вопрос", callback_data="ask_question")],
        ]
    )
    return keyboard


def get_documents_keyboard():
    """Клавиатура с документами и кнопкой Ознакомлен"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📄 Политика обработки данных",
                url="https://drive.google.com/file/d/1KJgS46UtyXzck2OHTdvpdeUa1axpRWhj/view?usp=drive_link"
            )],
            [InlineKeyboardButton(
                text="📄 Согласие на обработку данных",
                url="https://drive.google.com/file/d/1xu6uuVZEU5Z2kssZHnZUxNwX1J0f4QqH/view?usp=sharing"
            )],
            [InlineKeyboardButton(
                text="📄 Публичная оферта",
                url="https://drive.google.com/file/d/1xCuPXPQYc5LhFmOq3s9ZQMkcWGqC9T0E/view?usp=sharing"
            )],
            [InlineKeyboardButton(
                text="✅ ОЗНАКОМЛЕН ✅",
                callback_data="documents_accepted"
            )],
            [InlineKeyboardButton(text="← Назад", callback_data="back_main")],
        ]
    )
    return keyboard


def get_payment_keyboard():
    """Клавиатура выбора подписки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔹 1 месяц — 1990 руб.",
                callback_data="pay_1month"
            )],
            [InlineKeyboardButton(
                text="⭐ 3 месяца — 4990 руб. (выгода 980 руб.)",
                callback_data="pay_3months"
            )],
            [InlineKeyboardButton(text="← Назад", callback_data="back_main")],
        ]
    )
    return keyboard


def get_admin_keyboard():
    """Админская клавиатура"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Все пользователи", callback_data="admin_all_users"),
                InlineKeyboardButton(text="Оплатившие", callback_data="admin_paid_users")
            ],
            [
                InlineKeyboardButton(text="Не оплатившие", callback_data="admin_unpaid_users"),
                InlineKeyboardButton(text="Статистика", callback_data="admin_stats")
            ],
            [InlineKeyboardButton(text="Рассылка неоплатившим", callback_data="admin_broadcast_unpaid")],
            [InlineKeyboardButton(text="Написать пользователю", callback_data="admin_send_message")],
        ]
    )
    return keyboard


def get_back_keyboard():
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Назад в меню", callback_data="back_main")],
        ]
    )
    return keyboard


def get_cancel_keyboard():
    """Кнопка отмены"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="cancel_action")],
        ]
    )
    return keyboard


# Обработчики команд
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = message.from_user

    # Добавляем пользователя в базу и проверяем, новый ли он
    is_new_user = await db.add_user(
        user_id=user.id,
        username=user.username or "Не указан",
        full_name=user.full_name or "Не указано"
    )

    # Если новый пользователь - уведомляем админов
    if is_new_user:
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"Новый пользователь\n\n"
                    f"Имя: {user.full_name}\n"
                    f"Username: @{user.username or 'не указан'}\n"
                    f"ID: {user.id}",
                    parse_mode="HTML"
                )
            except:
                pass

    welcome_text = f"""👋 Привет, <b>{user.first_name}</b>!

Если вы чувствуете, что нейросети уже меняют рынок, а вы пока только смотрите со стороны — этот клуб для вас.

Каждый день появляются новые инструменты, фишки, обновления. Разбираться в этом в одиночку — долго. Покупать дорогие курсы — рискованно.

📲 <b>Мы сделали проще.</b>

Telegram-клуб по нейросетям — это целый месяц актуальной практики по цене одного мини-курса.

📚 <b>Внутри клуба:</b>
• 2 новых практических урока каждую неделю
• Готовые базы промтов — забираете и используете
• Живые эфиры раз в 2 недели с ответами на вопросы
• Поддержка и разборы от экспертов
• Концентрат пользы — применяете сразу

Это не «посмотреть и забыть». Это формат «взял — сделал — получил результат».

👥 <b>Кто ведёт клуб:</b>
🎨 Анна — AI creator и AI-художник
⚙️ Софья — эксперт по автоматизации

💰 <b>Доступ:</b>
• 1 месяц — 1990 руб.
• 3 месяца — 4990 руб.

Цена актуальна до 1 марта.

💡 <b>Готовы внутрь?</b>"""

    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("Нет доступа к админ-панели.")
        return

    await message.answer(
        "<b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("testcard"))
async def cmd_testcard(message: Message):
    """Добавить тестовую карту для скриншотов (только для админов)"""
    if message.from_user.id not in config.ADMIN_IDS:
        return

    # Добавляем тестовую карту
    await db.save_payment_token(message.from_user.id, "test_token_12345", "4242")

    await message.answer(
        "✅ Тестовая карта добавлена!\n\n"
        "Теперь зайди в «👤 Мой профиль» — там будет карта •••• 4242 и кнопка отвязки.\n\n"
        "После скриншотов можешь отвязать карту.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


# Callback обработчики главного меню
@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.edit_text(
        "Действие отменено.\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "info_club")
async def info_about_club(callback: CallbackQuery):
    """Информация о клубе"""
    info_text = """🚀 <b>AI Навигатор: Пульс Будущего</b>

Клуб по нейросетям в Telegram — актуальные уроки целый месяц от двух экспертов по цене миникурса.

📚 <b>Что вы получите:</b>
• 2 новых урока в неделю
• Готовые базы промтов
• Живые эфиры раз в 2 недели
• Поддержка экспертов
• Минимум воды — максимум пользы

👥 <b>Эксперты:</b>
🎨 Анна — AI creator и AI художник
⚙️ Софья — эксперт по автоматизации

💰 <b>Цены:</b>
• 1 месяц — 1990 руб.
• 3 месяца — 4990 руб.

Стоимость актуальна до 1 марта."""

    await callback.message.edit_text(info_text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "program")
async def show_program(callback: CallbackQuery):
    """Программа курса"""
    program_text = """📚 <b>Программа клуба на 3 месяца</b>

Новые уроки каждую неделю: вторник — Анна, четверг — Софья

✨ <b>Что входит:</b>
• Урок 0 — Подарок (вводные уроки уже доступны)
• Живые эфиры (2 в месяц — по одному от каждого эксперта)
• База промптов для генерации изображений
• База материалов и ссылок
• Личная поддержка в чате
• Комьюнити участников

⚙️ <b>Уроки Софьи (четверг):</b>
01. Нейросети с нуля: устанавливаем, оплачиваем
02. Язык нейросетей: промпты и логика
03. Карта нейросетей: какую выбрать
04. 50 лайфхаков для жизни с AI
05. AI-помощник для бизнеса и жизни
06. Глубокая кастомизация AI
07. Презентации и сайты за 10 минут
08. Мои любимые нейросети (разбор)
09. Генерация контента для соцсетей
10. AI-агент: автоматизация процессов
11. Создаём сайт с нуля (пошагово)
12. Создаём Telegram-бота за 30 минут

🎨 <b>Уроки Анны (вторник):</b>
01. Первые 60 минут в нейросетях: регистрация, оплата без карты
02. Создаем портфолио. Путь креатора
03. Создаем изображения в стиле модных журналов
04. Вписываем реальный товар в изображение
05. ИИ модель. Как создать и развивать
06. Быстрый контент на неделю: 20 изображений за 30 минут
07. Как создавать нейрофотосессию
08. Фотореализм за 3 шага
09. Midjourney. Самые главные кнопки для шедевров
10. Стиль бренда за один промпт
11. Видео из текста за 10 минут: ролики для Reels/Shorts
12. Создаем иллюстрации и разбираемся в стилях

📌 <b>Итог:</b> 8 полезных уроков и 2 эфира каждый месяц по цене миникурса"""

    await callback.message.edit_text(program_text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "payment_start")
async def payment_start(callback: CallbackQuery):
    """Начало процесса оплаты - показываем документы"""
    docs_text = """📋 <b>Перед оплатой</b>

Пожалуйста, ознакомьтесь с документами.

После ознакомления нажмите кнопку «Ознакомлен» для перехода к оплате.

💰 <b>Стоимость:</b>
• 1 месяц — 1990 руб.
• 3 месяца — 4990 руб. (выгода 980 руб.)"""

    await callback.message.edit_text(docs_text, reply_markup=get_documents_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "documents_accepted")
async def documents_accepted(callback: CallbackQuery):
    """Пользователь ознакомился с документами"""
    payment_text = """💳 <b>Выберите тариф</b>

🔹 <b>1 месяц — 1990 руб./мес</b>
• 8 уроков в месяц
• Готовые базы промтов
• Живые эфиры

⭐ <b>3 месяца — 4990 руб. каждые 3 мес</b>
• Всё из месячного тарифа
• Выгода 980 руб.
• Доступ на 3 месяца

🔄 <i>Это подписка с автопродлением. Следующий платёж произойдёт автоматически. Отменить можно в любой момент в профиле.</i>

Цены актуальны до 1 марта."""

    await callback.message.edit_text(payment_text, reply_markup=get_payment_keyboard(), parse_mode="HTML")
    await callback.answer("Спасибо за ознакомление!")


@router.callback_query(F.data == "pay_1month")
async def process_payment_1month(callback: CallbackQuery):
    """Оплата 1 месяц"""
    user = callback.from_user

    try:
        # Создаём платёж в ЮKassa с сохранением карты для автоплатежей
        payment = Payment.create({
            "amount": {
                "value": str(config.PRICE_1_MONTH) + ".00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/AInavigatorpulseofthefuture_bot"
            },
            "capture": True,
            "save_payment_method": "true",
            "description": f"AI Навигатор - подписка 1 месяц (ID: {user.id})",
            "metadata": {
                "user_id": str(user.id),
                "subscription_type": "1_month"
            }
        }, uuid.uuid4())

        payment_url = payment.confirmation.confirmation_url

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
                [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_payment_{payment.id}")],
                [InlineKeyboardButton(text="← Назад", callback_data="documents_accepted")],
            ]
        )

        await callback.message.edit_text(
            f"""💳 <b>Оплата — 1 месяц</b>

Стоимость: {config.PRICE_1_MONTH} руб./мес

🔄 <b>Это подписка.</b> Следующий платёж ({config.PRICE_1_MONTH} руб.) произойдёт автоматически через 30 дней.

Отменить подписку можно в любой момент в разделе «👤 Мой профиль».

Нажмите «Оплатить» для перехода на страницу оплаты.""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Ответ API: {e.response.text if hasattr(e.response, 'text') else e.response}")
        await callback.message.edit_text(
            f"Ошибка платежа: {str(e)[:300]}",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "pay_3months")
async def process_payment_3months(callback: CallbackQuery):
    """Оплата 3 месяца"""
    user = callback.from_user

    try:
        # Создаём платёж в ЮKassa с сохранением карты для автоплатежей
        payment = Payment.create({
            "amount": {
                "value": str(config.PRICE_3_MONTHS) + ".00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/AInavigatorpulseofthefuture_bot"
            },
            "capture": True,
            "save_payment_method": "true",
            "description": f"AI Навигатор - подписка 3 месяца (ID: {user.id})",
            "metadata": {
                "user_id": str(user.id),
                "subscription_type": "3_months"
            }
        }, uuid.uuid4())

        payment_url = payment.confirmation.confirmation_url

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
                [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_payment_{payment.id}")],
                [InlineKeyboardButton(text="← Назад", callback_data="documents_accepted")],
            ]
        )

        await callback.message.edit_text(
            f"""💳 <b>Оплата — 3 месяца</b>

Стоимость: {config.PRICE_3_MONTHS} руб. (выгода 980 руб.)

🔄 <b>Это подписка.</b> Следующий платёж ({config.PRICE_3_MONTHS} руб.) произойдёт автоматически через 3 месяца.

Отменить подписку можно в любой момент в разделе «👤 Мой профиль».

Нажмите «Оплатить» для перехода на страницу оплаты.""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Ответ API: {e.response.text if hasattr(e.response, 'text') else e.response}")
        await callback.message.edit_text(
            f"Ошибка платежа: {str(e)[:300]}",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery):
    """Проверка статуса оплаты"""
    payment_id = callback.data.replace("check_payment_", "")
    user = callback.from_user

    try:
        # Проверяем статус платежа
        payment = Payment.find_one(payment_id)

        if payment.status == "succeeded":
            # Платёж успешен
            metadata = payment.metadata
            subscription_type = metadata.get("subscription_type", "1_month")

            # Рассчитываем дату окончания подписки
            if subscription_type == "3_months":
                expiry_date = (datetime.now() + timedelta(days=90)).strftime("%d.%m.%Y")
                sub_name = "3 месяца"
                amount = config.PRICE_3_MONTHS
            else:
                expiry_date = (datetime.now() + timedelta(days=30)).strftime("%d.%m.%Y")
                sub_name = "1 месяц"
                amount = config.PRICE_1_MONTH

            # Сохраняем токен карты если есть
            if payment.payment_method and payment.payment_method.saved:
                card_last4 = payment.payment_method.card.last4 if payment.payment_method.card else "0000"
                await db.save_payment_token(user.id, payment.payment_method.id, card_last4)

            # Обновляем статус пользователя
            await db.mark_user_paid(user.id, subscription_type, expiry_date)

            # Сохраняем платёж
            await db.add_payment(user.id, amount, subscription_type, "succeeded", payment_id)

            # Уведомляем админов
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"💰 <b>Новая оплата!</b>\n\n"
                        f"Пользователь: {user.full_name}\n"
                        f"Username: @{user.username or 'не указан'}\n"
                        f"Тариф: {sub_name}\n"
                        f"Сумма: {amount} руб.\n"
                        f"Активен до: {expiry_date}",
                        parse_mode="HTML"
                    )
                except:
                    pass

            # Кнопка для входа в группу
            join_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Войти в клуб", url=config.CLUB_GROUP_LINK)],
                    [InlineKeyboardButton(text="← В меню", callback_data="back_main")],
                ]
            )

            await callback.message.edit_text(
                f"✅ <b>Оплата прошла успешно!</b>\n\n"
                f"Тариф: {sub_name}\n"
                f"Подписка активна до: {expiry_date}\n\n"
                f"🔄 Следующий платёж произойдёт автоматически.\n"
                f"Отменить подписку можно в любой момент в «👤 Мой профиль».\n\n"
                f"🎉 Добро пожаловать в клуб!\n\n"
                f"Нажмите кнопку ниже, чтобы присоединиться:",
                reply_markup=join_keyboard,
                parse_mode="HTML"
            )
            await callback.answer("Оплата подтверждена!")

        elif payment.status == "pending":
            await callback.answer("⏳ Платёж ещё обрабатывается. Подождите немного и попробуйте снова.", show_alert=True)

        elif payment.status == "canceled":
            await callback.message.edit_text(
                "❌ <b>Платёж отменён</b>\n\nПопробуйте оплатить снова.",
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer()

        else:
            await callback.answer(f"Статус платежа: {payment.status}", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка проверки платежа: {e}")
        await callback.answer("Ошибка проверки платежа. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "profile")
async def my_profile(callback: CallbackQuery):
    """Профиль пользователя"""
    user_data = await db.get_user(callback.from_user.id)

    if not user_data:
        await callback.message.edit_text(
            "Ошибка: данные не найдены. Используйте /start",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    status = "✅ Активна" if user_data["is_paid"] else "❌ Не оплачена"
    expiry = user_data["payment_expiry"] or "—"
    email = user_data["email"] or "Не указан"

    # Проверяем, есть ли привязанная карта
    card_info = await db.get_payment_token(callback.from_user.id)
    if card_info:
        card_text = f"💳 Карта: •••• {card_info['card_last4']}"
    else:
        card_text = "💳 Карта: не привязана"

    # Проверяем статус автопродления
    auto_renewal = await db.get_auto_renewal_status(callback.from_user.id)
    if card_info:
        auto_renewal_text = "✅ Включено" if auto_renewal else "❌ Отключено"
    else:
        auto_renewal_text = "— (нет карты)"

    profile_text = f"""👤 <b>Ваш профиль</b>

• Имя: {user_data['full_name']}
• Username: @{user_data['username']}
• Email: {email}
• Подписка: {status}
• Активна до: {expiry}
• {card_text}
• Автопродление: {auto_renewal_text}

Для изменения данных — задайте вопрос в поддержку."""

    # Создаём клавиатуру
    buttons = []
    if card_info:
        # Кнопка включения/отключения автопродления
        if auto_renewal:
            buttons.append([InlineKeyboardButton(text="🔕 Отключить автопродление", callback_data="toggle_auto_renewal_off")])
        else:
            buttons.append([InlineKeyboardButton(text="🔔 Включить автопродление", callback_data="toggle_auto_renewal_on")])
        buttons.append([InlineKeyboardButton(text="🗑 Отвязать карту", callback_data="unlink_card")])
    # Кнопка отмены подписки (если есть активная подписка)
    if user_data["is_paid"]:
        buttons.append([InlineKeyboardButton(text="❌ Отменить подписку", callback_data="cancel_subscription")])
    buttons.append([InlineKeyboardButton(text="← Назад в меню", callback_data="back_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(profile_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "unlink_card")
async def unlink_card_confirm(callback: CallbackQuery):
    """Подтверждение отвязки карты"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, отвязать", callback_data="unlink_card_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="profile")],
        ]
    )

    await callback.message.edit_text(
        "🗑 <b>Отвязать карту?</b>\n\n"
        "Данные вашей карты будут удалены. "
        "Для следующей оплаты потребуется ввести данные заново.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "unlink_card_confirm")
async def unlink_card_execute(callback: CallbackQuery):
    """Выполнение отвязки карты"""
    user = callback.from_user

    # Получаем инфо о карте перед удалением
    card_info = await db.get_payment_token(user.id)
    card_last4 = card_info['card_last4'] if card_info else "????"

    # Удаляем токен
    await db.delete_payment_token(user.id)

    # Уведомляем админов
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🗑 <b>Карта отвязана</b>\n\n"
                f"Пользователь: {user.full_name}\n"
                f"Username: @{user.username or 'не указан'}\n"
                f"ID: {user.id}\n"
                f"Карта: •••• {card_last4}",
                parse_mode="HTML"
            )
        except:
            pass

    await callback.message.edit_text(
        "✅ <b>Карта отвязана</b>\n\n"
        "Данные вашей карты успешно удалены из системы.",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Карта отвязана!")


@router.callback_query(F.data == "toggle_auto_renewal_off")
async def toggle_auto_renewal_off(callback: CallbackQuery):
    """Отключение автопродления"""
    user = callback.from_user

    await db.set_auto_renewal(user.id, False)

    # Уведомляем админов
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔕 <b>Автопродление отключено</b>\n\n"
                f"Пользователь: {user.full_name}\n"
                f"Username: @{user.username or 'не указан'}\n"
                f"ID: {user.id}",
                parse_mode="HTML"
            )
        except:
            pass

    await callback.message.edit_text(
        "🔕 <b>Автопродление отключено</b>\n\n"
        "Автоматическое списание отключено.\n"
        "Не забудьте продлить подписку вручную до её окончания.",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Автопродление отключено")


@router.callback_query(F.data == "toggle_auto_renewal_on")
async def toggle_auto_renewal_on(callback: CallbackQuery):
    """Включение автопродления"""
    user = callback.from_user

    await db.set_auto_renewal(user.id, True)

    # Уведомляем админов
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 <b>Автопродление включено</b>\n\n"
                f"Пользователь: {user.full_name}\n"
                f"Username: @{user.username or 'не указан'}\n"
                f"ID: {user.id}",
                parse_mode="HTML"
            )
        except:
            pass

    await callback.message.edit_text(
        "🔔 <b>Автопродление включено</b>\n\n"
        "Подписка будет автоматически продлеваться.\n"
        "За 3 дня до окончания вы получите уведомление о предстоящем списании.",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Автопродление включено")


@router.callback_query(F.data == "cancel_subscription")
async def cancel_subscription_confirm(callback: CallbackQuery):
    """Подтверждение отмены подписки"""
    user_data = await db.get_user(callback.from_user.id)
    expiry = user_data["payment_expiry"] if user_data else "—"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, отменить", callback_data="cancel_subscription_confirm")],
            [InlineKeyboardButton(text="❌ Нет, оставить", callback_data="profile")],
        ]
    )

    await callback.message.edit_text(
        f"❌ <b>Отменить подписку?</b>\n\n"
        f"Ваша подписка будет активна до {expiry}.\n"
        f"После этой даты доступ к материалам будет закрыт.\n\n"
        f"Также будут отключены:\n"
        f"• Автопродление\n"
        f"• Привязанная карта\n\n"
        f"Вы уверены?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_subscription_confirm")
async def cancel_subscription_execute(callback: CallbackQuery):
    """Выполнение отмены подписки"""
    user = callback.from_user
    user_data = await db.get_user(user.id)
    expiry = user_data["payment_expiry"] if user_data else "—"

    # Получаем инфо о карте перед удалением
    card_info = await db.get_payment_token(user.id)
    card_last4 = card_info['card_last4'] if card_info else None

    # Отключаем автопродление
    await db.set_auto_renewal(user.id, False)

    # Отвязываем карту если есть
    if card_info:
        await db.delete_payment_token(user.id)

    # Уведомляем админов
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"❌ <b>Подписка отменена</b>\n\n"
                f"Пользователь: {user.full_name}\n"
                f"Username: @{user.username or 'не указан'}\n"
                f"ID: {user.id}\n"
                f"Подписка активна до: {expiry}\n"
                f"Карта: {'•••• ' + card_last4 if card_last4 else 'не была привязана'}",
                parse_mode="HTML"
            )
        except:
            pass

    await callback.message.edit_text(
        f"❌ <b>Подписка отменена</b>\n\n"
        f"Ваша подписка будет активна до {expiry}.\n"
        f"После этой даты доступ будет закрыт.\n\n"
        f"Автопродление отключено.\n"
        f"{'Карта отвязана.' if card_last4 else ''}\n\n"
        f"Вы всегда можете оформить подписку заново через «💳 Оплатить доступ».",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Подписка отменена")


@router.callback_query(F.data == "ask_question")
async def ask_question(callback: CallbackQuery):
    """Задать вопрос"""
    question_text = """💬 <b>Задать вопрос</b>

Напишите ваш вопрос в ответ на это сообщение.

Эксперты ответят вам в ближайшее время ⚡"""

    await callback.message.edit_text(question_text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


# Админские callback'и
@router.callback_query(F.data == "admin_all_users")
async def admin_all_users(callback: CallbackQuery):
    """Список всех пользователей"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    users = await db.get_all_users()

    if not users:
        await callback.message.edit_text(
            "Пользователей пока нет.",
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()
        return

    text = "<b>Все пользователи:</b>\n\n"
    for user in users[:20]:
        paid_status = "+" if user["is_paid"] else "-"
        text += f"{paid_status} {user['full_name']} (@{user['username']}) — ID: {user['user_id']}\n"

    text += f"\nВсего: {len(users)}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_paid_users")
async def admin_paid_users(callback: CallbackQuery):
    """Список оплативших"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    users = await db.get_paid_users()

    if not users:
        await callback.message.edit_text(
            "Оплативших пользователей пока нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
            ])
        )
        await callback.answer()
        return

    text = "<b>Оплатившие пользователи:</b>\n\n"
    for user in users:
        text += f"+ {user['full_name']} (@{user['username']})\n"
        text += f"  Email: {user['email'] or 'Не указан'}\n"
        text += f"  До: {user['payment_expiry']}\n"
        text += f"  Тариф: {user['subscription_type']}\n\n"

    text += f"Всего оплативших: {len(users)}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_unpaid_users")
async def admin_unpaid_users(callback: CallbackQuery):
    """Список неоплативших"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    users = await db.get_unpaid_users()

    if not users:
        await callback.message.edit_text(
            "Все пользователи оплатили!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
            ])
        )
        await callback.answer()
        return

    text = "<b>Не оплатившие пользователи:</b>\n\n"
    for user in users[:20]:
        text += f"- {user['full_name']} (@{user['username']}) — ID: {user['user_id']}\n"

    text += f"\nВсего не оплативших: {len(users)}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика бота"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    users = await db.get_all_users()
    paid_users = await db.get_paid_users()
    unpaid_users = await db.get_unpaid_users()

    total_users = len(users)
    total_paid = len(paid_users)
    total_unpaid = len(unpaid_users)
    conversion_rate = (total_paid / total_users * 100) if total_users > 0 else 0

    stats_text = f"""<b>Статистика</b>

Всего пользователей: {total_users}
Оплатили подписку: {total_paid}
Не оплатили: {total_unpaid}
Конверсия: {conversion_rate:.1f}%

Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
        ]
    )

    await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast_unpaid")
async def admin_broadcast_unpaid_start(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку неоплатившим"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    unpaid_count = len(await db.get_unpaid_users())

    await callback.message.edit_text(
        f"<b>Рассылка неоплатившим</b>\n\n"
        f"Будет отправлено: {unpaid_count} пользователям\n\n"
        f"Введите текст сообщения для рассылки:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminBroadcast.waiting_for_broadcast_message)
    await callback.answer()


@router.message(AdminBroadcast.waiting_for_broadcast_message)
async def admin_broadcast_send(message: Message, state: FSMContext):
    """Отправить рассылку неоплатившим"""
    if message.from_user.id not in config.ADMIN_IDS:
        return

    unpaid_users = await db.get_unpaid_users()
    sent_count = 0
    failed_count = 0

    status_message = await message.answer("Отправка...")

    for user in unpaid_users:
        try:
            await bot.send_message(
                user['user_id'],
                message.text,
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Не удалось отправить сообщение {user['user_id']}: {e}")

    await status_message.edit_text(
        f"<b>Рассылка завершена</b>\n\n"
        f"Отправлено: {sent_count}\n"
        f"Не удалось: {failed_count}",
        parse_mode="HTML"
    )

    await state.clear()


@router.callback_query(F.data == "admin_send_message")
async def admin_send_message_start(callback: CallbackQuery, state: FSMContext):
    """Начать отправку сообщения пользователю"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "Введите ID пользователя:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminMessage.waiting_for_user_id)
    await callback.answer()


@router.message(AdminMessage.waiting_for_user_id)
async def admin_send_message_get_id(message: Message, state: FSMContext):
    """Получить ID пользователя"""
    if message.from_user.id not in config.ADMIN_IDS:
        return

    try:
        user_id = int(message.text)
        await state.update_data(target_user_id=user_id)
        await message.answer("Введите текст сообщения:", reply_markup=get_cancel_keyboard())
        await state.set_state(AdminMessage.waiting_for_message)
    except ValueError:
        await message.answer("Неверный формат ID. Введите число:")


@router.message(AdminMessage.waiting_for_message)
async def admin_send_message_send(message: Message, state: FSMContext):
    """Отправить сообщение пользователю"""
    if message.from_user.id not in config.ADMIN_IDS:
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    try:
        await bot.send_message(
            target_user_id,
            f"<b>Сообщение от поддержки:</b>\n\n{message.text}",
            parse_mode="HTML"
        )

        await db.add_message(target_user_id, "admin", message.text, is_from_admin=True)
        await message.answer("Сообщение отправлено!")
    except Exception as e:
        await message.answer(f"Ошибка отправки: {e}")

    await state.clear()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возврат в админ-панель"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# Обработчик сообщений от пользователей (вопросы)
@router.message(F.text)
async def handle_user_message(message: Message, state: FSMContext):
    """Обработка сообщений от пользователей"""
    # Проверяем, не в состоянии ли пользователь
    current_state = await state.get_state()
    if current_state:
        return

    # Сохраняем в БД
    await db.add_message(
        message.from_user.id,
        message.from_user.username or "unknown",
        message.text
    )

    # Уведомляем админов
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"<b>Новый вопрос</b>\n\n"
                f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"ID: {message.from_user.id}\n\n"
                f"Вопрос:\n{message.text}",
                parse_mode="HTML"
            )
        except:
            pass

    await message.answer(
        "✅ <b>Вопрос получен!</b>\n\nЭксперты ответят вам в ближайшее время ⚡",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


async def auto_renew_subscription(user_id: int, username: str, full_name: str, subscription_type: str) -> bool:
    """
    Автоматическое продление подписки через сохранённую карту.
    Продлевает по тому же тарифу, что был у пользователя.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        # Получаем токен карты
        card_info = await db.get_payment_token(user_id)
        if not card_info:
            logger.warning(f"Нет токена карты для пользователя {user_id}")
            return False

        payment_token = card_info['payment_token']

        # Определяем сумму и срок в зависимости от типа подписки
        if subscription_type == "3_months":
            amount = config.PRICE_3_MONTHS
            days = 90
            sub_name = "3 месяца"
            sub_type_auto = "3_months_auto"
        else:
            amount = config.PRICE_1_MONTH
            days = 30
            sub_name = "1 месяц"
            sub_type_auto = "1_month_auto"

        # Создаём автоплатёж через ЮKassa
        payment = Payment.create({
            "amount": {
                "value": str(amount) + ".00",
                "currency": "RUB"
            },
            "capture": True,
            "payment_method_id": payment_token,
            "description": f"AI Навигатор - автопродление подписки {sub_name} (ID: {user_id})",
            "metadata": {
                "user_id": str(user_id),
                "subscription_type": subscription_type,
                "auto_renewal": "true"
            }
        }, uuid.uuid4())

        # Проверяем статус платежа
        if payment.status == "succeeded":
            # Продлеваем подписку
            await db.extend_subscription(user_id, days)

            # Получаем новую дату окончания
            user_data = await db.get_user(user_id)
            new_expiry = user_data['payment_expiry'] if user_data else "неизвестно"

            # Сохраняем платёж
            await db.add_payment(user_id, amount, sub_type_auto, "succeeded", payment.id)

            # Уведомляем пользователя
            try:
                await bot.send_message(
                    user_id,
                    f"✅ <b>Подписка автоматически продлена!</b>\n\n"
                    f"Тариф: {sub_name}\n"
                    f"С вашей карты списано {amount} руб.\n"
                    f"Подписка активна до: {new_expiry}\n\n"
                    f"Для отключения автопродления перейдите в «👤 Мой профиль».",
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

            # Уведомляем админов
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"🔄 <b>Автопродление подписки</b>\n\n"
                        f"Пользователь: {full_name}\n"
                        f"Username: @{username or 'не указан'}\n"
                        f"Тариф: {sub_name}\n"
                        f"Сумма: {amount} руб.\n"
                        f"Новая дата окончания: {new_expiry}",
                        parse_mode="HTML"
                    )
                except:
                    pass

            logger.info(f"Автопродление успешно для пользователя {user_id}, тариф {sub_name}")
            return True

        elif payment.status == "pending":
            # Платёж ещё обрабатывается - это редко для автоплатежей
            logger.info(f"Автоплатёж pending для пользователя {user_id}")
            return False

        else:
            # Платёж не прошёл
            logger.warning(f"Автоплатёж не прошёл для пользователя {user_id}: статус {payment.status}")
            return False

    except Exception as e:
        logger.error(f"Ошибка автопродления для пользователя {user_id}: {e}")
        return False


async def check_expiring_subscriptions():
    """Фоновая задача для проверки истекающих подписок"""
    while True:
        try:
            logger.info("Проверка истекающих подписок...")

            # 1. Уведомления за 3 дня до окончания
            users_expiring_soon = await db.get_users_expiring_soon(days=3)
            for user in users_expiring_soon:
                # Определяем сумму в зависимости от типа подписки
                if user.get('subscription_type') == "3_months":
                    amount = config.PRICE_3_MONTHS
                    period = "3 месяца"
                else:
                    amount = config.PRICE_1_MONTH
                    period = "1 месяц"

                try:
                    await bot.send_message(
                        user['user_id'],
                        f"⏰ <b>Напоминание о подписке</b>\n\n"
                        f"Через 3 дня с вашей карты •••• {user['card_last4']} будет списано {amount} руб. "
                        f"для продления подписки ({period}).\n\n"
                        f"Если вы хотите отключить автопродление, сделайте это в разделе «👤 Мой профиль».",
                        parse_mode="HTML",
                        reply_markup=get_main_keyboard()
                    )
                    logger.info(f"Отправлено уведомление о скором списании пользователю {user['user_id']}")
                except Exception as e:
                    logger.error(f"Не удалось отправить напоминание пользователю {user['user_id']}: {e}")

            # 2. Автопродление подписок, истекающих сегодня
            users_expiring_today = await db.get_users_expiring_today()
            for user in users_expiring_today:
                success = await auto_renew_subscription(
                    user['user_id'],
                    user['username'],
                    user['full_name'],
                    user.get('subscription_type', '1_month')
                )

                if not success:
                    # Уведомляем пользователя об ошибке
                    try:
                        await bot.send_message(
                            user['user_id'],
                            f"❌ <b>Не удалось продлить подписку</b>\n\n"
                            f"Автоматическое списание не прошло.\n"
                            f"Пожалуйста, продлите подписку вручную через «💳 Оплатить доступ».",
                            parse_mode="HTML",
                            reply_markup=get_main_keyboard()
                        )
                    except Exception as e:
                        logger.error(f"Не удалось уведомить пользователя {user['user_id']} об ошибке: {e}")

                    # Уведомляем админов
                    for admin_id in config.ADMIN_IDS:
                        try:
                            await bot.send_message(
                                admin_id,
                                f"⚠️ <b>Ошибка автопродления</b>\n\n"
                                f"Пользователь: {user['full_name']}\n"
                                f"Username: @{user['username'] or 'не указан'}\n"
                                f"ID: {user['user_id']}",
                                parse_mode="HTML"
                            )
                        except:
                            pass

            logger.info("Проверка истекающих подписок завершена")

        except Exception as e:
            logger.error(f"Ошибка в check_expiring_subscriptions: {e}")

        # Ждём 24 часа до следующей проверки
        await asyncio.sleep(24 * 60 * 60)


async def main():
    """Запуск бота"""
    # Инициализация БД
    await db.init_db()
    logger.info("База данных инициализирована")

    # Регистрируем роутер
    dp.include_router(router)

    # Запускаем фоновую задачу проверки подписок
    asyncio.create_task(check_expiring_subscriptions())
    logger.info("Фоновая задача проверки подписок запущена")

    # Запускаем polling
    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
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
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from database import Database
import config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
db = Database(config.DATABASE_PATH)


# Состояния для FSM
class UserRegistration(StatesGroup):
    waiting_for_email = State()
    waiting_for_phone = State()


class AdminMessage(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_message = State()


# Клавиатуры
def get_main_keyboard():
    """Главное меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ℹ️ Информация о клубе")],
            [KeyboardButton(text="💳 Оплатить подписку")],
            [KeyboardButton(text="❓ Задать вопрос")],
            [KeyboardButton(text="👤 Мой профиль")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_payment_keyboard():
    """Клавиатура выбора подписки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц — 1990₽", callback_data="pay_1month")],
            [InlineKeyboardButton(text="3 месяца — 4990₽", callback_data="pay_3months")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
        ]
    )
    return keyboard


def get_admin_keyboard():
    """Админская клавиатура"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_all_users")],
            [InlineKeyboardButton(text="💰 Оплатившие", callback_data="admin_paid_users")],
            [InlineKeyboardButton(text="💬 Последние сообщения", callback_data="admin_messages")],
            [InlineKeyboardButton(text="✉️ Отправить сообщение", callback_data="admin_send_message")],
        ]
    )
    return keyboard


def get_cancel_keyboard():
    """Кнопка отмены"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
    return keyboard


# Обработчики команд
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = message.from_user

    # Добавляем пользователя в базу
    await db.add_user(
        user_id=user.id,
        username=user.username or "Не указан",
        full_name=user.full_name or "Не указано"
    )

    welcome_text = f"""
👋 Привет, {user.first_name}!

Добро пожаловать в **AI Навигатор: Пульс Будущего** — клуб по изучению нейросетей!

🤖 Здесь вы получите:
• Актуальные уроки от экспертов
• Готовые промты и базы знаний
• Живое общение и поддержку

Выберите действие в меню ⬇️
"""

    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔️ У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "🔧 **Админ-панель**\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )


# Обработчики кнопок главного меню
@router.message(F.text == "ℹ️ Информация о клубе")
async def info_about_club(message: Message):
    """Информация о клубе"""
    await message.answer(config.CLUB_INFO, parse_mode="Markdown")


@router.message(F.text == "💳 Оплатить подписку")
async def payment_menu(message: Message):
    """Меню оплаты"""
    text = """
💳 **Выберите тариф:**

**1 месяц — 1990₽**
• 8-9 уроков в месяц
• Готовые базы промтов
• Живые эфиры

**3 месяца — 4990₽**
• Всё из месячного тарифа
• Выгода 980₽
• Доступ на 3 месяца

⚡️ Цены актуальны до 1 февраля!
"""

    await message.answer(text, reply_markup=get_payment_keyboard(), parse_mode="Markdown")


@router.message(F.text == "❓ Задать вопрос")
async def ask_question(message: Message):
    """Задать вопрос"""
    await message.answer(
        "✍️ Напишите ваш вопрос, и эксперты ответят вам в ближайшее время:",
        reply_markup=get_cancel_keyboard()
    )


@router.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message):
    """Профиль пользователя"""
    user_data = await db.get_user(message.from_user.id)

    if not user_data:
        await message.answer("❌ Ошибка: данные не найдены. Используйте /start")
        return

    status = "✅ Активна" if user_data["is_paid"] else "❌ Не оплачена"
    expiry = user_data["payment_expiry"] or "—"
    email = user_data["email"] or "Не указан"

    profile_text = f"""
👤 **Ваш профиль**

**Имя:** {user_data['full_name']}
**Username:** @{user_data['username']}
**Email:** {email}
**Подписка:** {status}
**Активна до:** {expiry}

Для изменения данных напишите в поддержку.
"""

    await message.answer(profile_text, parse_mode="Markdown")


# Обработчик callback-кнопок
@router.callback_query(F.data == "pay_1month")
async def process_payment_1month(callback: CallbackQuery, state: FSMContext):
    """Оплата 1 месяц"""
    await callback.message.answer(
        f"""
💳 **Оплата подписки: 1 месяц**

Стоимость: **{config.PRICE_1_MONTH}₽**

Для оплаты перейдите по ссылке:
[Ссылка на оплату будет добавлена после настройки ЮKassa]

После оплаты доступ будет активирован автоматически!
""",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "pay_3months")
async def process_payment_3months(callback: CallbackQuery, state: FSMContext):
    """Оплата 3 месяца"""
    await callback.message.answer(
        f"""
💳 **Оплата подписки: 3 месяца**

Стоимость: **{config.PRICE_3_MONTHS}₽**
Выгода: **980₽**

Для оплаты перейдите по ссылке:
[Ссылка на оплату будет добавлена после настройки ЮKassa]

После оплаты доступ будет активирован автоматически!
""",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.delete()
    await callback.message.answer("Выберите действие:", reply_markup=get_main_keyboard())
    await callback.answer()


# Админские callback'и
@router.callback_query(F.data == "admin_all_users")
async def admin_all_users(callback: CallbackQuery):
    """Список всех пользователей"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    users = await db.get_all_users()

    if not users:
        await callback.message.answer("Пользователей пока нет.")
        await callback.answer()
        return

    text = "👥 **Все пользователи:**\n\n"
    for user in users[:20]:  # Первые 20
        paid_status = "✅" if user["is_paid"] else "❌"
        text += f"{paid_status} {user['full_name']} (@{user['username']}) — ID: `{user['user_id']}`\n"

    text += f"\n📊 Всего пользователей: {len(users)}"

    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_paid_users")
async def admin_paid_users(callback: CallbackQuery):
    """Список оплативших"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    users = await db.get_paid_users()

    if not users:
        await callback.message.answer("Оплативших пользователей пока нет.")
        await callback.answer()
        return

    text = "💰 **Оплатившие пользователи:**\n\n"
    for user in users:
        text += f"✅ {user['full_name']} (@{user['username']})\n"
        text += f"   📧 {user['email'] or 'Не указан'}\n"
        text += f"   📅 До: {user['payment_expiry']}\n"
        text += f"   💳 {user['subscription_type']}\n\n"

    text += f"📊 Всего оплативших: {len(users)}"

    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_messages")
async def admin_messages(callback: CallbackQuery):
    """Последние сообщения"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    messages = await db.get_all_messages()

    if not messages:
        await callback.message.answer("Сообщений пока нет.")
        await callback.answer()
        return

    text = "💬 **Последние 20 сообщений:**\n\n"
    for msg in messages[:20]:
        sender = "👨‍💼 Админ" if msg["is_from_admin"] else f"👤 @{msg['username']}"
        text += f"{sender} ({msg['timestamp'][:16]}):\n"
        text += f"_{msg['message_text'][:100]}_\n\n"

    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_send_message")
async def admin_send_message_start(callback: CallbackQuery, state: FSMContext):
    """Начать отправку сообщения пользователю"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await callback.message.answer(
        "Введите ID пользователя, которому хотите отправить сообщение:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminMessage.waiting_for_user_id)
    await callback.answer()


@router.message(AdminMessage.waiting_for_user_id)
async def admin_send_message_get_id(message: Message, state: FSMContext):
    """Получить ID пользователя"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_main_keyboard())
        return

    try:
        user_id = int(message.text)
        await state.update_data(target_user_id=user_id)
        await message.answer("Теперь введите текст сообщения:")
        await state.set_state(AdminMessage.waiting_for_message)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число:")


@router.message(AdminMessage.waiting_for_message)
async def admin_send_message_send(message: Message, state: FSMContext):
    """Отправить сообщение пользователю"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_main_keyboard())
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    try:
        # Отправляем сообщение пользователю
        await bot.send_message(
            target_user_id,
            f"💬 **Сообщение от поддержки:**\n\n{message.text}",
            parse_mode="Markdown"
        )

        # Сохраняем в БД
        await db.add_message(target_user_id, "admin", message.text, is_from_admin=True)

        await message.answer("✅ Сообщение отправлено!", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

    await state.clear()


# Обработчик вопросов от пользователей
@router.message(F.text & ~F.text.in_(["ℹ️ Информация о клубе", "💳 Оплатить подписку",
                                       "❓ Задать вопрос", "👤 Мой профиль", "❌ Отмена"]))
async def handle_user_message(message: Message):
    """Обработка сообщений от пользователей (вопросы)"""
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
                f"❓ **Новый вопрос от пользователя**\n\n"
                f"👤 {message.from_user.full_name} (@{message.from_user.username})\n"
                f"🆔 ID: `{message.from_user.id}`\n\n"
                f"💬 {message.text}",
                parse_mode="Markdown"
            )
        except:
            pass

    await message.answer(
        "✅ Ваш вопрос получен! Эксперты ответят в ближайшее время.",
        reply_markup=get_main_keyboard()
    )


# Обработчик отмены
@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_keyboard())


async def main():
    """Запуск бота"""
    # Инициализация БД
    await db.init_db()
    logger.info("База данных инициализирована")

    # Регистрируем роутер
    dp.include_router(router)

    # Запускаем polling
    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

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
                text="✅ Ознакомлен",
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
Темы скоро будут объявлены

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

🔹 <b>1 месяц — 1990 руб.</b>
• 8 уроков в месяц
• Готовые базы промтов
• Живые эфиры

⭐ <b>3 месяца — 4990 руб.</b>
• Всё из месячного тарифа
• Выгода 980 руб.
• Доступ на 3 месяца

Цены актуальны до 1 марта."""

    await callback.message.edit_text(payment_text, reply_markup=get_payment_keyboard(), parse_mode="HTML")
    await callback.answer("Спасибо за ознакомление!")


@router.callback_query(F.data == "pay_1month")
async def process_payment_1month(callback: CallbackQuery):
    """Оплата 1 месяц"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад к тарифам", callback_data="documents_accepted")],
            [InlineKeyboardButton(text="В главное меню", callback_data="back_main")],
        ]
    )

    await callback.message.edit_text(
        f"""<b>Оплата — 1 месяц</b>

Стоимость: {config.PRICE_1_MONTH} руб.

Для оплаты перейдите по ссылке:
[Ссылка будет добавлена после настройки ЮKassa]

После оплаты доступ активируется автоматически.""",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "pay_3months")
async def process_payment_3months(callback: CallbackQuery):
    """Оплата 3 месяца"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад к тарифам", callback_data="documents_accepted")],
            [InlineKeyboardButton(text="В главное меню", callback_data="back_main")],
        ]
    )

    await callback.message.edit_text(
        f"""<b>Оплата — 3 месяца</b>

Стоимость: {config.PRICE_3_MONTHS} руб.
Выгода: 980 руб.

Для оплаты перейдите по ссылке:
[Ссылка будет добавлена после настройки ЮKassa]

После оплаты доступ активируется автоматически.""",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


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

    profile_text = f"""👤 <b>Ваш профиль</b>

• Имя: {user_data['full_name']}
• Username: @{user_data['username']}
• Email: {email}
• Подписка: {status}
• Активна до: {expiry}

Для изменения данных — задайте вопрос в поддержку."""

    await callback.message.edit_text(profile_text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


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

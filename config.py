import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8203221474:AAGWWVpf2XCwdP3Vyvhjy0p_tTqm6iLdvuU")

# Admin user IDs
ADMIN_IDS = [590597992, 554519803]  # Софья Маковень, Анна Алпатова

# ЮKassa настройки
YUKASSA_SHOP_ID = "1258598"
YUKASSA_SECRET_KEY = ""  # DISABLED - payments turned off

# Ссылка на группу клуба
CLUB_GROUP_LINK = "https://t.me/+VKGe-NTkq1hkOTEy"

# Цены
PRICE_1_MONTH = 1990
PRICE_3_MONTHS = 4990

# База данных PostgreSQL
DATABASE_URL = "postgresql://postgres:QCycHWqIdMXCVzyLPsxPxcAqDhysAEgK@switchyard.proxy.rlwy.net:15637/railway"

# Информация о клубе
CLUB_INFO = """
🚀 **AI Навигатор: Пульс Будущего**

Клуб по нейросетям в Telegram — актуальные уроки целый месяц от двух экспертов по цене миникурса.

📚 **Что вы получите:**
• 2 новых урока в неделю
• Готовые базы промтов
• Живые эфиры раз в 2 недели
• Поддержка экспертов
• Минимум воды — максимум пользы

👥 **Эксперты:**
• Анна — AI creator и AI художник
• Софья — эксперт по автоматизации

💰 **Цены:**
• 1 месяц — 1990₽
• 3 месяца — 4990₽

Стоимость актуальна до 1 февраля, затем будет повышение!
"""

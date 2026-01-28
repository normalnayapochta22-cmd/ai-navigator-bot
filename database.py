import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    email TEXT,
                    phone TEXT,
                    registration_date TEXT,
                    is_paid BOOLEAN DEFAULT 0,
                    payment_expiry TEXT,
                    subscription_type TEXT
                )
            """)

            # Таблица платежей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    subscription_type TEXT,
                    payment_date TEXT,
                    payment_status TEXT,
                    yukassa_payment_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица сообщений (для переписки)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    message_text TEXT,
                    timestamp TEXT,
                    is_from_admin BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            await db.commit()

    async def add_user(self, user_id: int, username: str, full_name: str) -> bool:
        """Добавить нового пользователя. Возвращает True если пользователь новый."""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, существует ли пользователь
            async with db.execute("""
                SELECT user_id FROM users WHERE user_id = ?
            """, (user_id,)) as cursor:
                existing = await cursor.fetchone()

            if existing:
                return False  # Пользователь уже существует

            # Добавляем нового пользователя
            await db.execute("""
                INSERT INTO users (user_id, username, full_name, registration_date)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, full_name, datetime.now().isoformat()))
            await db.commit()
            return True  # Новый пользователь

    async def update_user_email(self, user_id: int, email: str):
        """Обновить email пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET email = ? WHERE user_id = ?
            """, (email, user_id))
            await db.commit()

    async def update_user_phone(self, user_id: int, phone: str):
        """Обновить телефон пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET phone = ? WHERE user_id = ?
            """, (phone, user_id))
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить данные пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    async def mark_user_paid(self, user_id: int, subscription_type: str, expiry_date: str):
        """Отметить пользователя как оплатившего"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users
                SET is_paid = 1, subscription_type = ?, payment_expiry = ?
                WHERE user_id = ?
            """, (subscription_type, expiry_date, user_id))
            await db.commit()

    async def add_payment(self, user_id: int, amount: int, subscription_type: str,
                         payment_status: str, yukassa_payment_id: str = ""):
        """Добавить запись о платеже"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO payments (user_id, amount, subscription_type, payment_date,
                                    payment_status, yukassa_payment_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, amount, subscription_type, datetime.now().isoformat(),
                  payment_status, yukassa_payment_id))
            await db.commit()

    async def add_message(self, user_id: int, username: str, message_text: str,
                         is_from_admin: bool = False):
        """Сохранить сообщение в историю"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO messages (user_id, username, message_text, timestamp, is_from_admin)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, message_text, datetime.now().isoformat(), is_from_admin))
            await db.commit()

    async def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users ORDER BY registration_date DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_paid_users(self) -> List[Dict]:
        """Получить только оплативших пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users WHERE is_paid = 1 ORDER BY payment_expiry DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_user_messages(self, user_id: int) -> List[Dict]:
        """Получить переписку с пользователем"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM messages WHERE user_id = ? ORDER BY timestamp ASC
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_messages(self) -> List[Dict]:
        """Получить все сообщения"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM messages ORDER BY timestamp DESC LIMIT 100
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

import asyncpg
from datetime import datetime
from typing import Optional, List, Dict

import config


class Database:
    def __init__(self):
        self.pool = None

    async def init_db(self):
        """Инициализация базы данных"""
        self.pool = await asyncpg.create_pool(config.DATABASE_URL)

        async with self.pool.acquire() as conn:
            # Таблица пользователей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    email TEXT,
                    phone TEXT,
                    registration_date TEXT,
                    is_paid BOOLEAN DEFAULT FALSE,
                    payment_expiry TEXT,
                    subscription_type TEXT,
                    payment_token TEXT,
                    card_last4 TEXT,
                    auto_renewal BOOLEAN DEFAULT TRUE
                )
            """)

            # Добавляем колонку auto_renewal если её нет (для существующих БД)
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'users' AND column_name = 'auto_renewal'
                    ) THEN
                        ALTER TABLE users ADD COLUMN auto_renewal BOOLEAN DEFAULT TRUE;
                    END IF;
                END $$;
            """)

            # Таблица платежей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    amount INTEGER,
                    subscription_type TEXT,
                    payment_date TEXT,
                    payment_status TEXT,
                    yukassa_payment_id TEXT
                )
            """)

            # Таблица сообщений
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    message_text TEXT,
                    timestamp TEXT,
                    is_from_admin BOOLEAN DEFAULT FALSE
                )
            """)

    async def add_user(self, user_id: int, username: str, full_name: str) -> bool:
        """Добавить нового пользователя. Возвращает True если пользователь новый."""
        async with self.pool.acquire() as conn:
            # Проверяем, существует ли пользователь
            existing = await conn.fetchrow(
                "SELECT user_id FROM users WHERE user_id = $1", user_id
            )

            if existing:
                return False

            # Добавляем нового пользователя
            await conn.execute("""
                INSERT INTO users (user_id, username, full_name, registration_date)
                VALUES ($1, $2, $3, $4)
            """, user_id, username, full_name, datetime.now().isoformat())
            return True

    async def update_user_email(self, user_id: int, email: str):
        """Обновить email пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET email = $1 WHERE user_id = $2", email, user_id
            )

    async def update_user_phone(self, user_id: int, phone: str):
        """Обновить телефон пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET phone = $1 WHERE user_id = $2", phone, user_id
            )

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить данные пользователя"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )
            if row:
                return dict(row)
            return None

    async def mark_user_paid(self, user_id: int, subscription_type: str, expiry_date: str):
        """Отметить пользователя как оплатившего"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users
                SET is_paid = TRUE, subscription_type = $1, payment_expiry = $2
                WHERE user_id = $3
            """, subscription_type, expiry_date, user_id)

    async def add_payment(self, user_id: int, amount: int, subscription_type: str,
                         payment_status: str, yukassa_payment_id: str = ""):
        """Добавить запись о платеже"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO payments (user_id, amount, subscription_type, payment_date,
                                    payment_status, yukassa_payment_id)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, user_id, amount, subscription_type, datetime.now().isoformat(),
                  payment_status, yukassa_payment_id)

    async def add_message(self, user_id: int, username: str, message_text: str,
                         is_from_admin: bool = False):
        """Сохранить сообщение в историю"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO messages (user_id, username, message_text, timestamp, is_from_admin)
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, username, message_text, datetime.now().isoformat(), is_from_admin)

    async def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users ORDER BY registration_date DESC"
            )
            return [dict(row) for row in rows]

    async def get_paid_users(self) -> List[Dict]:
        """Получить только оплативших пользователей"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users WHERE is_paid = TRUE ORDER BY payment_expiry DESC"
            )
            return [dict(row) for row in rows]

    async def get_user_messages(self, user_id: int) -> List[Dict]:
        """Получить переписку с пользователем"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM messages WHERE user_id = $1 ORDER BY timestamp ASC", user_id
            )
            return [dict(row) for row in rows]

    async def get_all_messages(self) -> List[Dict]:
        """Получить все сообщения"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM messages ORDER BY timestamp DESC LIMIT 100"
            )
            return [dict(row) for row in rows]

    async def get_unpaid_users(self) -> List[Dict]:
        """Получить пользователей, которые не оплатили"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users WHERE is_paid = FALSE ORDER BY registration_date DESC"
            )
            return [dict(row) for row in rows]

    async def save_payment_token(self, user_id: int, payment_token: str, card_last4: str):
        """Сохранить токен карты для автоплатежей"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET payment_token = $1, card_last4 = $2 WHERE user_id = $3
            """, payment_token, card_last4, user_id)

    async def delete_payment_token(self, user_id: int):
        """Удалить токен карты (отвязать карту)"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET payment_token = NULL, card_last4 = NULL WHERE user_id = $1
            """, user_id)

    async def get_payment_token(self, user_id: int) -> Optional[Dict]:
        """Получить токен карты пользователя"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT payment_token, card_last4 FROM users WHERE user_id = $1", user_id
            )
            if row and row['payment_token']:
                return {'payment_token': row['payment_token'], 'card_last4': row['card_last4']}
            return None

    async def get_auto_renewal_status(self, user_id: int) -> bool:
        """Получить статус автопродления"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT auto_renewal FROM users WHERE user_id = $1", user_id
            )
            if row:
                return row['auto_renewal'] if row['auto_renewal'] is not None else True
            return True

    async def set_auto_renewal(self, user_id: int, enabled: bool):
        """Установить статус автопродления"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET auto_renewal = $1 WHERE user_id = $2", enabled, user_id
            )

    async def get_users_expiring_today(self) -> List[Dict]:
        """Получить пользователей с подпиской, истекающей сегодня"""
        today = datetime.now().strftime("%d.%m.%Y")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM users
                WHERE is_paid = TRUE
                AND payment_expiry = $1
                AND auto_renewal = TRUE
                AND payment_token IS NOT NULL
            """, today)
            return [dict(row) for row in rows]

    async def get_users_expiring_soon(self, days: int = 3) -> List[Dict]:
        """Получить пользователей для уведомления о скором окончании подписки"""
        from datetime import timedelta
        target_date = (datetime.now() + timedelta(days=days)).strftime("%d.%m.%Y")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM users
                WHERE is_paid = TRUE
                AND payment_expiry = $1
                AND auto_renewal = TRUE
                AND payment_token IS NOT NULL
            """, target_date)
            return [dict(row) for row in rows]

    async def extend_subscription(self, user_id: int, days: int = 30):
        """Продлить подписку на указанное количество дней"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT payment_expiry FROM users WHERE user_id = $1", user_id
            )
            if row and row['payment_expiry']:
                # Парсим текущую дату окончания
                current_expiry = datetime.strptime(row['payment_expiry'], "%d.%m.%Y")
                # Добавляем дни
                from datetime import timedelta
                new_expiry = (current_expiry + timedelta(days=days)).strftime("%d.%m.%Y")
                await conn.execute(
                    "UPDATE users SET payment_expiry = $1 WHERE user_id = $2",
                    new_expiry, user_id
                )

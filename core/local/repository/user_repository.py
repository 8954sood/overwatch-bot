import aiosqlite
from typing import Optional, List
import datetime
from core.model import User, ActivityLog, ActivityStats, ActivityLeaderboardEntry


class UserRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def get_or_create_user(self, user_id: int, display_name: str) -> User:
        await self.db.execute(
            "INSERT OR IGNORE INTO users (user_id, display_name) VALUES (?, ?)",
            (user_id, display_name)
        )
        await self.db.execute(
            "UPDATE users SET display_name = ? WHERE user_id = ?",
            (display_name, user_id)
        )
        cursor = await self.db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        await self.db.commit()
        return User(user_id=row['user_id'], display_name=row['display_name'], balance=row['balance'])

    async def get_user(self, user_id: int) -> Optional[User]:
        cursor = await self.db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return User(user_id=row['user_id'], display_name=row['display_name'], balance=row['balance'])

    async def update_balance(self, user_id: int, amount_change: int) -> int:
        cursor = await self.db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ? RETURNING balance",
            (amount_change, user_id)
        )
        new_balance = await cursor.fetchone()
        await self.db.commit()
        return new_balance[0]

    async def get_balance_leaderboard(self, limit: int = 10) -> List[User]:
        cursor = await self.db.execute("SELECT * FROM users ORDER BY balance DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [User(user_id=r['user_id'], display_name=r['display_name'], balance=r['balance']) for r in rows]

    async def log_message_activity(self, user_id: int):
        today = datetime.date.today().isoformat()
        await self.db.execute(
            "INSERT INTO daily_activity (user_id, activity_date, message_count) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, activity_date) DO UPDATE SET message_count = message_count + 1",
            (user_id, today)
        )
        await self.update_balance(user_id, 2)

    async def log_voice_activity(self, user_id: int, duration: int):
        today = datetime.date.today().isoformat()
        cursor = await self.db.execute(
            "SELECT voice_seconds FROM daily_activity WHERE user_id = ? AND activity_date = ?", (user_id, today)
        )
        current_seconds = (await cursor.fetchone() or (0,))[0]

        total_seconds = current_seconds + duration
        new_rewards = ((total_seconds // 3600) - (current_seconds // 3600)) * 600

        if new_rewards > 0:
            await self.update_balance(user_id, new_rewards)

        await self.db.execute(
            "INSERT INTO daily_activity (user_id, activity_date, voice_seconds) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, activity_date) DO UPDATE SET voice_seconds = voice_seconds + ?",
            (user_id, today, duration, duration)
        )
        await self.db.commit()

    async def get_activity_stats(self, user_id: int, start_date: str, end_date: str) -> ActivityStats:
        cursor = await self.db.execute(
            "SELECT SUM(message_count), SUM(voice_seconds) FROM daily_activity "
            "WHERE user_id = ? AND activity_date BETWEEN ? AND ?",
            (user_id, start_date, end_date)
        )
        row = await cursor.fetchone()
        return ActivityStats(
            total_messages=row[0] or 0,
            total_voice_minutes=(row[1] or 0) // 60
        )

    async def get_activity_leaderboard(self, limit: int = 10) -> List[ActivityLeaderboardEntry]:
        cursor = await self.db.execute(
            "SELECT u.user_id, u.display_name, "
            "COALESCE(SUM(a.message_count), 0) AS messages, "
            "COALESCE(SUM(a.voice_seconds) / 60, 0) AS voice_minutes, "
            "COALESCE(SUM(a.message_count), 0) + COALESCE(SUM(a.voice_seconds) / 60, 0) AS points "
            "FROM users u "
            "LEFT JOIN daily_activity a ON u.user_id = a.user_id "
            "GROUP BY u.user_id "
            "ORDER BY points DESC "
            "LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [
            ActivityLeaderboardEntry(
                user_id=r["user_id"],
                display_name=r["display_name"],
                total_messages=int(r["messages"] or 0),
                total_voice_minutes=int(r["voice_minutes"] or 0),
            )
            for r in rows
        ]

    async def reset_all_balances(self) -> None:
        await self.db.execute("UPDATE users SET balance = 0")
        await self.db.commit()

    async def set_birthday(self, user_id: int, birthday: str) -> None:
        await self.db.execute(
            "UPDATE users SET birthday = ? WHERE user_id = ?",
            (birthday, user_id)
        )
        await self.db.commit()

    async def get_users_with_birthday(self, today: str) -> List[User]:
        cursor = await self.db.execute(
            "SELECT * FROM users WHERE birthday = ?", (today,)
        )
        rows = await cursor.fetchall()
        return [User(user_id=r['user_id'], display_name=r['display_name'], balance=r['balance'], birthday=r['birthday']) for r in rows]

    async def update_display_name(self, user_id: int, new_display_name: str) -> None:
        await self.db.execute(
            "UPDATE users SET display_name = ? WHERE user_id = ?",
            (new_display_name, user_id)
        )
        await self.db.commit()
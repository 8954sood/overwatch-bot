import aiosqlite
import datetime
from typing import List

class ModerationRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def add_warning(self, user_id: int, moderator_id: int, reason: str, count: int) -> int:
        now = datetime.datetime.utcnow().isoformat()
        cursor = await self.db.execute(
            "INSERT INTO moderation_logs (user_id, moderator_id, action, reason, count, created_at) "
            "VALUES (?, ?, 'WARN', ?, ?, ?)",
            (user_id, moderator_id, reason, count, now)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def add_ban(self, user_id: int, moderator_id: int, reason: str) -> int:
        now = datetime.datetime.utcnow().isoformat()
        cursor = await self.db.execute(
            "INSERT INTO moderation_logs (user_id, moderator_id, action, reason, created_at) "
            "VALUES (?, ?, 'BAN', ?, ?)",
            (user_id, moderator_id, reason, now)
        )
        await self.db.commit()
        return cursor.lastrowid

import aiosqlite
import datetime
from typing import List
from core.model import ModerationLog

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

    async def get_user_logs(self, user_id: int) -> List[ModerationLog]:
        cursor = await self.db.execute(
            "SELECT * FROM moderation_logs WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [ModerationLog(**row) for row in rows]

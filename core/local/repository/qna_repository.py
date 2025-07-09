import aiosqlite
from typing import Optional, List
from core.model.qna_models import QnaChannel


class QnaRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def add_channel(self, channel_id: int, guild_id: int) -> QnaChannel:
        cursor = await self.db.execute(
            "INSERT INTO qna_channels (channel_id, guild_id) VALUES (?, ?) RETURNING *",
            (channel_id, guild_id),
        )
        row = await cursor.fetchone()
        await self.db.commit()
        return QnaChannel.from_row(dict(row))

    async def remove_channel(self, channel_id: int) -> bool:
        cursor = await self.db.execute("DELETE FROM qna_channels WHERE channel_id = ?", (channel_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    async def get_channel_by_id(self, channel_id: int) -> Optional[QnaChannel]:
        cursor = await self.db.execute("SELECT * FROM qna_channels WHERE channel_id = ?", (channel_id,))
        row = await cursor.fetchone()
        return QnaChannel.from_row(dict(row)) if row else None

    async def get_all_channels(self) -> List[QnaChannel]:
        cursor = await self.db.execute("SELECT * FROM qna_channels")
        rows = await cursor.fetchall()
        return [QnaChannel.from_row(dict(r)) for r in rows]

    async def update_pinned_message(self, channel_id: int, message_id: int, title: str, content: str) -> bool:
        cursor = await self.db.execute(
            """
            UPDATE qna_channels
            SET pinned_message_id = ?, pinned_title = ?, pinned_content = ?
            WHERE channel_id = ?
            """,
            (message_id, title, content, channel_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def remove_pinned_message(self, channel_id: int) -> bool:
        cursor = await self.db.execute(
            """
            UPDATE qna_channels
            SET pinned_message_id = NULL, pinned_title = NULL, pinned_content = NULL
            WHERE channel_id = ?
            """,
            (channel_id,),
        )
        await self.db.commit()
        return cursor.rowcount > 0
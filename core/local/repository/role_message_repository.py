import json
from typing import Optional, List

import aiosqlite

from core.model.role_message_models import RoleMessage, RoleButton


class RoleMessageRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create_role_message(self, guild_id: int, channel_id: int, message_id: int, content: str, color: str) -> None:
        query = "INSERT INTO role_messages (guild_id, channel_id, message_id, content, color, role_buttons) VALUES (?, ?, ?, ?, ?, ?)"
        await self.db.execute(query, (guild_id, channel_id, message_id, content, color, json.dumps([])))
        await self.db.commit()

    async def get_by_channel_id(self, channel_id: int) -> Optional[RoleMessage]:
        query = "SELECT * FROM role_messages WHERE channel_id = ?"
        cursor = await self.db.execute(query, (channel_id,))
        row = await cursor.fetchone()
        return RoleMessage.from_row(row) if row else None

    async def get_all(self) -> List[RoleMessage]:
        query = "SELECT * FROM role_messages"
        cursor = await self.db.execute(query)
        rows = await cursor.fetchall()
        return [RoleMessage.from_row(row) for row in rows]

    async def update_message(self, channel_id: int, content: str, color: str) -> None:
        query = "UPDATE role_messages SET content = ?, color = ? WHERE channel_id = ?"
        await self.db.execute(query, (content, color, channel_id))
        await self.db.commit()

    async def update_buttons(self, channel_id: int, buttons: List[RoleButton]) -> None:
        buttons_json = json.dumps([b.__dict__ for b in buttons])
        query = "UPDATE role_messages SET role_buttons = ? WHERE channel_id = ?"
        await self.db.execute(query, (buttons_json, channel_id))
        await self.db.commit()

    async def delete_role_message(self, channel_id: int) -> None:
        query = "DELETE FROM role_messages WHERE channel_id = ?"
        await self.db.execute(query, (channel_id,))
        await self.db.commit()

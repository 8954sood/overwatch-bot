import aiosqlite
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class AutoVcGenerator:
    generator_channel_id: int
    category_id: int
    base_name: str
    guild_id: int

class AutoVcRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def add_generator(self, generator_channel_id: int, category_id: int, base_name: str, guild_id: int) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO auto_vc_generators (generator_channel_id, category_id, base_name, guild_id) "
            "VALUES (?, ?, ?, ?)",
            (generator_channel_id, category_id, base_name, guild_id)
        )
        await self.db.commit()

    async def get_generator(self, generator_channel_id: int) -> Optional[AutoVcGenerator]:
        cursor = await self.db.execute("SELECT * FROM auto_vc_generators WHERE generator_channel_id = ?", (generator_channel_id,))
        row = await cursor.fetchone()
        return AutoVcGenerator(**row) if row else None

    async def get_all_generators(self, guild_id: int) -> List[AutoVcGenerator]:
        cursor = await self.db.execute("SELECT * FROM auto_vc_generators WHERE guild_id = ?", (guild_id,))
        rows = await cursor.fetchall()
        return [AutoVcGenerator(**row) for row in rows]

    async def remove_generator(self, generator_channel_id: int) -> None:
        await self.db.execute("DELETE FROM auto_vc_generators WHERE generator_channel_id = ?", (generator_channel_id,))
        await self.db.commit()

    # --- Managed Channels --- #

    async def add_managed_channel(self, channel_id: int, owner_id: int, guild_id: int, generator_channel_id: int) -> None:
        await self.db.execute(
            "INSERT INTO managed_auto_vc_channels (channel_id, owner_id, guild_id, generator_channel_id) VALUES (?, ?, ?, ?)",
            (channel_id, owner_id, guild_id, generator_channel_id)
        )
        await self.db.commit()

    async def remove_managed_channel(self, channel_id: int) -> None:
        await self.db.execute("DELETE FROM managed_auto_vc_channels WHERE channel_id = ?", (channel_id,))
        await self.db.commit()

    async def get_all_managed_channels(self) -> List[int]:
        cursor = await self.db.execute("SELECT channel_id FROM managed_auto_vc_channels")
        rows = await cursor.fetchall()
        return [row['channel_id'] for row in rows]

    async def get_channel_owner(self, channel_id: int) -> Optional[int]:
        cursor = await self.db.execute("SELECT owner_id FROM managed_auto_vc_channels WHERE channel_id = ?", (channel_id,))
        row = await cursor.fetchone()
        return row['owner_id'] if row else None

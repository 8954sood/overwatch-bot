import aiosqlite
from typing import Optional, List
from core.model import ShopItem, InventoryItem, TemporaryRole

class ShopRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def add_item(self, **kwargs) -> ShopItem:
        keys = ', '.join(kwargs.keys())
        placeholders = ', '.join('?' * len(kwargs))
        cursor = await self.db.execute(
            f"INSERT INTO shop_items ({keys}) VALUES ({placeholders}) RETURNING *",
            tuple(kwargs.values())
        )
        row = await cursor.fetchone()
        await self.db.commit()
        return ShopItem(**dict(row))

    async def remove_item_by_name(self, name: str) -> bool:
        cursor = await self.db.execute("DELETE FROM shop_items WHERE name = ?", (name,))
        await self.db.commit()
        return cursor.rowcount > 0

    async def get_all_items(self) -> List[ShopItem]:
        cursor = await self.db.execute("SELECT * FROM shop_items ORDER BY price")
        rows = await cursor.fetchall()
        return [ShopItem(**dict(r)) for r in rows]

    async def get_item_by_id(self, item_id: int) -> Optional[ShopItem]:
        cursor = await self.db.execute("SELECT * FROM shop_items WHERE id = ?", (item_id,))
        row = await cursor.fetchone()
        return ShopItem(**dict(row)) if row else None

    async def get_user_inventory(self, user_id: int) -> List[InventoryItem]:
        cursor = await self.db.execute(
            "SELECT s.name, COUNT(i.id) as count FROM user_inventory i "
            "JOIN shop_items s ON i.shop_item_id = s.id "
            "WHERE i.user_id = ? GROUP BY s.name",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [InventoryItem(name=r['name'], count=r['count']) for r in rows]

    async def add_to_inventory(self, user_id: int, shop_item_id: int):
        await self.db.execute(
            "INSERT INTO user_inventory (user_id, shop_item_id) VALUES (?, ?)",
            (user_id, shop_item_id)
        )
        await self.db.commit()

    async def add_temporary_role(self, user_id: int, role_id: int, expires_at: str):
        await self.db.execute(
            "INSERT INTO temporary_roles (user_id, role_id, expires_at) VALUES (?, ?, ?)",
            (user_id, role_id, expires_at)
        )
        await self.db.commit()

    async def get_expired_roles(self, now_iso: str) -> List[TemporaryRole]:
        cursor = await self.db.execute(
            "SELECT * FROM temporary_roles WHERE expires_at <= ?", (now_iso,)
        )
        rows = await cursor.fetchall()
        return [TemporaryRole(**dict(r)) for r in rows]

    async def remove_temporary_roles_by_ids(self, ids: List[int]):
        if not ids: return
        placeholders = ', '.join('?' * len(ids))
        await self.db.execute(f"DELETE FROM temporary_roles WHERE id IN ({placeholders})", ids)
        await self.db.commit()
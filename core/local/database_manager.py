import os

import aiosqlite
import discord
from datetime import datetime

from core.local.repository import UserRepository, ShopRepository

DB_PATH = './database.db'

class DatabaseManager:
    def __init__(self, connection: aiosqlite.Connection):
        self._db = connection
        self.users = UserRepository(self._db)
        self.shop = ShopRepository(self._db)

    @classmethod
    async def create(cls):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        connection = await aiosqlite.connect(DB_PATH)
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA foreign_keys = ON;")

        with open('./core/local/schema.sql', 'r') as f:
            await connection.executescript(f.read())
        await connection.commit()

        return cls(connection)

    async def close(self):
        await self._db.close()
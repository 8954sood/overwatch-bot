import os

import aiosqlite
import discord
from datetime import datetime

from core.local.repository import UserRepository, ShopRepository
from core.local.repository.auto_vc_repository import AutoVcRepository
from core.local.repository.moderation_repository import ModerationRepository
from core.local.repository.role_message_repository import RoleMessageRepository
from core.local.repository.qna_repository import QnaRepository

DB_PATH = './database.db'

class DatabaseManager:
    DB_VERSION = 1

    def __init__(self, connection: aiosqlite.Connection):
        self._db = connection
        self.users = UserRepository(self._db)
        self.shop = ShopRepository(self._db)
        self.moderation = ModerationRepository(self._db)
        self.auto_vc = AutoVcRepository(self._db)
        self.role_message = RoleMessageRepository(self._db)
        self.qna = QnaRepository(self._db)

    @classmethod
    async def create(cls):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        connection = await aiosqlite.connect(DB_PATH)
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA foreign_keys = ON;")

        with open('./core/local/schema.sql', 'r') as f:
            await connection.executescript(f.read())
        await connection.commit()

        # 현재 버전 확인
        current_version = await cls._get_db_version(connection)

        if current_version < cls.DB_VERSION:
            print(f"🔄 Migrating DB from version {current_version} to {cls.DB_VERSION}")
            await cls._migrate(connection, current_version)
        elif current_version > cls.DB_VERSION:
            raise Exception(f"⚠️ DB version ({current_version}) is newer than supported version ({cls.DB_VERSION})")

        return cls(connection)

    @staticmethod
    async def _get_db_version(connection: aiosqlite.Connection) -> int:
        async with connection.execute("SELECT value FROM db_meta WHERE key = 'version'") as cursor:
            row = await cursor.fetchone()
            return int(row['value']) if row else 0

    @classmethod
    async def _migrate(cls, connection: aiosqlite.Connection, current_version: int):
        """
        데이터베이스 스키마를 최신 버전으로 마이그레이션합니다.

        이 함수는 현재 데이터베이스 버전(`db_meta` 테이블의 version 값)과
        코드 상의 최신 버전(`DB_VERSION`)을 비교하여, 중간에 필요한 SQL 마이그레이션
        파일들을 순차적으로 실행합니다. 각 버전의 마이그레이션 파일은
        `core/local/migrations/{버전}.sql` 형식으로 저장되어 있어야 합니다.

        마이그레이션 작성 가이드:
            1. DB 구조 변경 시 `DB_VERSION`을 1 증가시킵니다.
            2. `core/local/migrations/{DB_VERSION}.sql` 파일을 생성합니다.
            3. 해당 버전에서 필요한 SQL 변경 내용을 작성합니다.
               예: ALTER TABLE, CREATE TABLE, DROP COLUMN 등
            4. 파일명은 반드시 버전 숫자와 일치해야 하며, 중복되면 안 됩니다.
            5. 마이그레이션 완료 후 자동으로 `db_meta`의 version 값이 갱신됩니다.

        주의사항:
            - 마이그레이션 적용 전 데이터 백업을 권장합니다.
            - SQL 문법 오류나 논리 오류가 있으면 전체 마이그레이션이 실패할 수 있습니다.
            - 항상 테스트 환경에서 먼저 적용해보는 것이 좋습니다.
        """
        for version in range(current_version + 1, cls.DB_VERSION + 1):
            migration_file = f'./core/local/migrations/{version}.sql'
            if not os.path.exists(migration_file):
                raise Exception(f"Migration file {migration_file} not found.")

            print(f"📄 Applying migration {version}.sql")
            with open(migration_file, 'r') as f:
                await connection.executescript(f.read())

        await connection.execute("UPDATE db_meta SET value = ? WHERE key = 'version'", (str(cls.DB_VERSION),))
        await connection.commit()

    async def close(self):
        await self._db.close()
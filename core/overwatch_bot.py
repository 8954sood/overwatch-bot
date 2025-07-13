import os
import traceback

import aiosqlite
import discord
from discord.ext import commands

from core.local.database_manager import DatabaseManager

class OverwatchBot(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db: DatabaseManager | None = None
        self.guild_id = int(os.getenv("GUILD_ID"))
        print(self.guild_id)


        """
        특정 서버에서만 구동되도록 전역 Cog에 적용되는 설정입니다.
        """
        @self.check
        async def globally_check_guild(ctx: commands.Context) -> bool:
            if ctx.guild is None or ctx.guild.id != self.guild_id:
                ctx.guild_check_failed = True
                return False
            return True

    async def setup_hook(self) -> None:
        """
        봇이 디스코드에 로그인하기 전에 비동기적으로 실행되는 초기화 함수입니다.
        DB 연결, 테이블 생성, Cog 로딩 등을 처리하기에 가장 적합한 위치입니다.
        """
        # 1. DatabaseManager 인스턴스 생성 및 DB 연결/초기화
        #    DatabaseManager.create()는 aiosqlite 연결 및 스키마 실행을 담당합니다.
        print("Connecting to the database...")
        self.db = await DatabaseManager.create()
        print("Database connected and schema verified.")

        # 2. Cogs 폴더에서 Cog 파일들을 동적으로 로드
        print("Loading cogs...")
        for filename in os.listdir("./cogs"):
            # .py로 끝나고, __init__.py가 아닌 파일만 대상으로 함
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    # 파일명에서 .py를 제거하여 모듈 경로 생성 (e.g., cogs.economy)
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Successfully loaded cog: {filename}')
                except Exception as e:
                    # Cog 로딩 중 에러 발생 시 콘솔에 출력
                    print(f'❌ Failed to load cog {filename}: {e}')
                    # traceback을 함께 출력하면 디버깅에 더 용이합니다.
                    # import traceback
                    # traceback.print_exc()

        # 3. 애플리케이션 커맨드(슬래시 커맨드)를 지정된 길드에 동기화
        #    개발 중에는 특정 길드에만 동기화하여 빠른 테스트가 가능합니다.
        #    전역 커맨드로 배포할 경우 이 부분을 수정해야 합니다.
        print("Syncing command tree...")
        guild_obj = discord.Object(id=self.guild_id)
        self.tree.clear_commands(guild=guild_obj)
        # await self.tree.sync(guild=guild_obj)
        # print("Clear command tree.")

        self.tree.copy_global_to(guild=guild_obj)
        await self.tree.sync(guild=guild_obj)
        print("Command tree synced.")

    async def on_ready(self):
        """
        봇이 준비되었을 때 호출되는 이벤트. 봇의 정보와 준비 완료 메시지를 출력합니다.
        """
        print('------')
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Discord.py Version: {discord.__version__}')
        print('Bot is ready and online!')
        print('------')

    async def close(self):
        """
        봇이 종료될 때 호출됩니다. DB 연결을 안전하게 닫습니다.
        """
        if self.db:
            await self.db.close()
            print("Database connection closed.")
        await super().close()

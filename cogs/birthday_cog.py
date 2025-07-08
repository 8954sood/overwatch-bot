from datetime import timezone, timedelta

import discord
import pytz
from discord.ext import commands, tasks
from discord import app_commands
import datetime
from core.overwatch_bot import OverwatchBot

KST = timezone(timedelta(hours=9)) #datetime.datetime.now().astimezone().tzinfo #//pytz.timezone("Asia/Seoul")

class BirthdayCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot

    async def cog_load(self):
        if not self.check_birthdays.is_running():
            print("[TASK] check_birthdays Started.")
            self.check_birthdays.start()
            print(f"[TASK] check_birthdays {self.check_birthdays.next_iteration}")

    def cog_unload(self):
        self.check_birthdays.cancel()

    @app_commands.command(name="생일등록", description="당신의 생일을 등록합니다. (예: 01-15)")
    @app_commands.describe(생일="3월 8일 -> 03-08")
    async def register_birthday(self, interaction: discord.Interaction, 생일: str):
        try:
            datetime.datetime.strptime(생일, "%m-%d")
        except ValueError:
            await interaction.response.send_message("생일 형식은 MM-DD 여야 합니다. (예: 01-15)", ephemeral=True)
            return

        await self.bot.db.users.get_or_create_user(interaction.user.id, interaction.user.display_name)
        await self.bot.db.users.set_birthday(interaction.user.id, 생일)
        await interaction.response.send_message(f"{interaction.user.mention}님의 생일이 {생일}로 등록되었습니다.", ephemeral=True)

    @tasks.loop(time=datetime.time(hour=11, minute=16, tzinfo=KST))  # 매일 자정에 실행
    async def check_birthdays(self):
        print("check_birthdays")
        today = datetime.datetime.now(tz=KST).strftime("%m-%d")
        users = await self.bot.db.users.get_users_with_birthday(today)
        channel = self.bot.get_channel(1076722349489012776)
        birthday_user = []
        for user in users:
            birthday_user.append(f"<@{user.user_id}>")
        if channel:
            await channel.send(f"🎉 {", ".join(birthday_user)}님의 생일을 축하합니다! 🎉")

async def setup(bot: OverwatchBot):
    await bot.add_cog(BirthdayCog(bot))

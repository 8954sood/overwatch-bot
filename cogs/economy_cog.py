import discord
from discord import app_commands
from discord.ext import commands
import datetime

from core import OverwatchBot
from core.utiles import money_to_string


class EconomyCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot

    @app_commands.command(name="잔고", description="자신 또는 다른 유저의 재화를 확인합니다.")
    @app_commands.describe(유저="잔고를 확인할 유저")
    async def balance(self, interaction: discord.Interaction, 유저: discord.User = None):
        target = 유저 or interaction.user
        user_model = await self.bot.db.users.get_or_create_user(target.id, target.display_name)
        embed = discord.Embed(
            description=f"💰 **{user_model.display_name}**님의 현재 잔고는 **{money_to_string(user_model.balance)}** 입니다.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="인벤토리", description="자신의 아이템 보유 현황을 확인합니다.")
    async def inventory(self, interaction: discord.Interaction, 유저: discord.User = None):
        target = 유저 or interaction.user
        await self.bot.db.users.get_or_create_user(target.id, target.display_name)
        inventory_items = await self.bot.db.shop.get_user_inventory(target.id)

        if not inventory_items:
            description = "보유한 아이템이 없습니다."
        else:
            description = "\n".join(f"- {item.name}: {item.count}개" for item in inventory_items)

        embed = discord.Embed(title=f"{target.display_name}님의 인벤토리", description=description,
                              color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="송금", description="다른 유저에게 재화를 보냅니다.")
    @app_commands.describe(받는분="재화를 받을 유저", 금액="보낼 재화의 양")
    async def transfer(self, interaction: discord.Interaction, 받는분: discord.User, 금액: app_commands.Range[int, 1]):
        if interaction.user.id == 받는분.id:
            return await interaction.response.send_message("자기 자신에게 송금할 수 없습니다.", ephemeral=True)
        if 받는분.bot:
            return await interaction.response.send_message("봇에게는 송금할 수 없습니다.", ephemeral=True)

        sender_model = await self.bot.db.users.get_or_create_user(interaction.user.id, interaction.user.display_name)
        if sender_model.balance < 금액:
            return await interaction.response.send_message("잔고가 부족합니다.", ephemeral=True)

        await self.bot.db.users.get_or_create_user(받는분.id, 받는분.display_name)
        await self.bot.db.users.update_balance(interaction.user.id, -금액)
        await self.bot.db.users.update_balance(받는분.id, 금액)

        await interaction.response.send_message(f"{받는분.mention}님에게 {money_to_string(금액)}을 성공적으로 보냈습니다.")

    @app_commands.command(name="랭킹", description="서버 내 재화 랭킹을 확인합니다.")
    async def leaderboard(self, interaction: discord.Interaction):
        leaderboard_users = await self.bot.db.users.get_balance_leaderboard()
        description = []
        medals = ["🥇", "🥈", "🥉"]
        for i, user in enumerate(leaderboard_users):
            rank = medals[i] if i < 3 else f"{i + 1}."
            description.append(f"{rank} **{user.display_name}**: {money_to_string(user.balance)}")

        embed = discord.Embed(title="재화 랭킹", description="\n".join(description), color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="활동량", description="자신 또는 다른 유저의 활동량을 확인합니다.")
    @app_commands.describe(유저="활동량을 확인할 유저", 시작일="YYYY-MM-DD 형식", 종료일="YYYY-MM-DD 형식")
    async def activity(self, interaction: discord.Interaction, 유저: discord.User = None, 시작일: str = None,
                       종료일: str = None):
        target = 유저 or interaction.user

        # 날짜 유효성 검사 및 기본값 설정
        try:
            end_date = datetime.datetime.strptime(종료일, "%Y-%m-%d").date() if 종료일 else datetime.date.today()
            start_date = datetime.datetime.strptime(시작일, "%Y-%m-%d").date() if 시작일 else end_date - datetime.timedelta(
                days=6)
        except ValueError:
            return await interaction.response.send_message("날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).", ephemeral=True)

        stats = await self.bot.db.users.get_activity_stats(target.id, start_date.isoformat(), end_date.isoformat())

        embed = discord.Embed(
            title=f"{target.display_name}님의 활동량",
            description=f"기간: {start_date} ~ {end_date}",
            color=discord.Color.purple()
        )
        embed.add_field(name="💬 메시지 수", value=f"{stats.total_messages}개", inline=True)
        embed.add_field(name="🎙️ 음성 활동 시간", value=f"{stats.total_voice_minutes}분", inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
import os
from typing import Union, Optional

import discord
from discord import app_commands, Interaction
from discord.app_commands import Command, ContextMenu
from discord.ext import commands
import datetime
import random
import asyncio

from core import OverwatchBot
from core.utiles import money_to_string


class EconomyCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        self.cooldowns = {}  # {command_name: {user_id: cooldown_end_time}}
        self.ladder_cooldown = datetime.timedelta(hours=2)
        self.slot_machine_cooldown = datetime.timedelta(hours=2)
        self.emojis = {
            '메달': os.getenv("GAMBLE_1_EMOJI"),
            '보석': os.getenv("GAMBLE_2_EMOJI"),
            '달러': os.getenv("GAMBLE_3_EMOJI"),
            '주머니': os.getenv("GAMBLE_4_EMOJI"),
            '100': os.getenv("GAMBLE_5_EMOJI"),
            'wheel1': os.getenv("GAMBLE_A1_EMOJI"),
            'wheel2': os.getenv("GAMBLE_A2_EMOJI"),
            'wheel3': os.getenv("GAMBLE_A3_EMOJI"),
        }

    def check_cooldown(self, command_name: str, user_id: int, cooldown: datetime.timedelta):
        now = datetime.datetime.now()
        command_cooldowns = self.cooldowns.get(command_name, {})
        cooldown_end = command_cooldowns.get(user_id)

        if cooldown_end and cooldown_end > now:
            remaining = (cooldown_end - now).total_seconds()
            raise discord.app_commands.CommandOnCooldown(
                cooldown=discord.app_commands.Cooldown(1, cooldown.total_seconds()),
                retry_after=remaining
            )

    def set_cooldown(self, command_name: str, user_id: int, duration: datetime.timedelta):
        now = datetime.datetime.now()
        if command_name not in self.cooldowns:
            self.cooldowns[command_name] = {}
        self.cooldowns[command_name][user_id] = now + duration

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

    @app_commands.command(name="재화지급", description="유저에게 재화를 지급합니다.")
    @app_commands.rename(user="대상", money="금액")
    @app_commands.describe(user="재화를 지급할 대상을 지정해주세요", money="재화의 지급량을 지정해주세요")
    @app_commands.checks.has_permissions(administrator=True)
    async def give_money(self, interaction: Interaction, user: discord.User, money: int):
        before_user = await self.bot.db.users.get_or_create_user(user.id, user.display_name)
        now_money = await self.bot.db.users.update_balance(user.id, money)

        await interaction.response.send_message(f"{user.mention}님 에게 {money_to_string(money)}을 지급하였습니다.\n-# {money_to_string(before_user.balance)} -> {money_to_string(now_money)}", ephemeral=True)

    @app_commands.command(name="노동", description="노동을 통해 재화를 획득합니다. (쿨타임: 1시간)")
    @app_commands.checks.cooldown(1, 3600)
    async def labor(self, interaction: Interaction):
        await interaction.response.defer()
        user = await self.bot.db.users.get_or_create_user(interaction.user.id, interaction.user.display_name)

        chance = random.random() * 100
        if chance <= 49.99999:
            amount = random.randint(0, 10)
        elif chance <= 79.99999:
            amount = random.randint(10, 30)
        elif chance <= 92.99999:
            amount = random.randint(30, 50)
        elif chance <= 97.99999:
            amount = random.randint(50, 100)
        elif chance <= 99.49999:
            amount = random.randint(100, 500)
        elif chance <= 99.99999:
            amount = random.randint(500, 1000)
        else:
            amount = random.randint(1000, 10000)

        await self.bot.db.users.update_balance(user.user_id, amount)
        embed = discord.Embed(description=f"노동을 통해 {money_to_string(amount)} 재화를 획득했습니다.", color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="사다리타기", description="사다리 게임으로 재산을 증식시키세요! (쿨타임: 2시간)")
    @app_commands.describe(베팅금액="베팅할 금액 (최소 100)", 배팅위치="좌, 중, 우 중 하나를 선택하세요.")
    @app_commands.choices(배팅위치=[
        app_commands.Choice(name="좌", value="좌"),
        app_commands.Choice(name="중", value="중"),
        app_commands.Choice(name="우", value="우"),
    ])
    async def ladder(self, interaction: Interaction, 베팅금액: app_commands.Range[int, 100], 배팅위치: app_commands.Choice[str]):
        self.check_cooldown("ladder", interaction.user.id, self.ladder_cooldown)
        await interaction.response.defer()
        user = await self.bot.db.users.get_or_create_user(interaction.user.id, interaction.user.display_name)

        if user.balance < 베팅금액:
            return await interaction.followup.send("잔고가 부족합니다.", ephemeral=True)

        positions = ["좌", "중", "우"]
        actual_result = random.choice(positions)

        if actual_result == 배팅위치.value:
            reward = 베팅금액 * 2
            new_balance = await self.bot.db.users.update_balance(user.user_id, reward)
            result_message = f"축하합니다! 사다리 결과는 **{actual_result}**입니다. {money_to_string(reward)} 재화를 획득했습니다!\n**{interaction.user.display_name}**님의 잔액: {money_to_string(new_balance)}(+{money_to_string(reward)})"
            color = discord.Color.green()
        else:
            new_balance = await self.bot.db.users.update_balance(user.user_id, -베팅금액)
            result_message = f"아쉽습니다. 사다리 결과는 **{actual_result}**입니다. {money_to_string(베팅금액)} 재화를 잃었습니다.\n**{interaction.user.display_name}**님의 잔액: {money_to_string(new_balance)}(-{money_to_string(베팅금액)})"
            color = discord.Color.red()


        self.set_cooldown("ladder", interaction.user.id, self.ladder_cooldown)
        embed = discord.Embed(title="사다리타기", description=f"선택한 위치: **{배팅위치.value}**\n결과: **{actual_result}**\n\n{result_message}", color=color)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="슬롯머신", description="슬롯머신을 돌려 행운을 시험하세요! (쿨타임: 2시간)")
    @app_commands.describe(베팅금액="베팅할 금액 (최소 100)")
    async def slot_machine(self, interaction: Interaction, 베팅금액: app_commands.Range[int, 100]):
        self.check_cooldown("slot_machine", interaction.user.id, self.slot_machine_cooldown)
        user = await self.bot.db.users.get_or_create_user(interaction.user.id, interaction.user.display_name)
        if user.balance < 베팅금액:
            return await interaction.response.send_message("잔고가 부족합니다.", ephemeral=True)

        embed = discord.Embed(title="슬롯머신", description="슬롯머신을 돌리고 있습니다.", color=discord.Color.gold())
        await interaction.response.send_message(content=f"{self.emojis['wheel1']}{self.emojis['wheel2']}{self.emojis['wheel3']}", embeds=[embed])

        await asyncio.sleep(1.8)

        chance = random.random() * 100
        multiplier = 0
        result_emojis = []

        if chance <= 79.99999:  # 꽝
            multiplier = 0
            result_emojis = random.sample(list(self.emojis.values())[:-3], 3)
        elif chance <= 89.99999:  # 메달
            multiplier = 2
            result_emojis = [self.emojis['메달']] * 3
        elif chance <= 94.99999:  # 보석
            multiplier = 3
            result_emojis = [self.emojis['보석']] * 3
        elif chance <= 97.49999:  # 달러
            multiplier = 5
            result_emojis = [self.emojis['달러']] * 3
        elif chance <= 99.49999:  # 주머니
            multiplier = 7
            result_emojis = [self.emojis['주머니']] * 3
        else:  # 100
            multiplier = 10
            result_emojis = [self.emojis['100']] * 3

        winnings = int(베팅금액 * multiplier)
        final_balance_change = winnings - 베팅금액
        new_balance = await self.bot.db.users.update_balance(user.user_id, final_balance_change)

        if multiplier == 0:
            description = f"아쉽습니다. {money_to_string(베팅금액)}을 잃었습니다.\n**{interaction.user.display_name}**님의 잔액: {money_to_string(new_balance)}(-{money_to_string(베팅금액)})"
            color = discord.Color.red()
        else:
            description = f"축하합니다! {money_to_string(winnings)}을 얻었습니다. (배율: {multiplier}배)\n\n**{interaction.user.display_name}**님의 잔액: {money_to_string(new_balance)}(+{money_to_string(winnings)})"
            color = discord.Color.green()

        self.set_cooldown("slot_machine", interaction.user.id, self.slot_machine_cooldown)
        embed = discord.Embed(title="슬롯머신", description=description, color=color)
        await interaction.edit_original_response(content="".join(result_emojis), embeds=[embed])

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))

import os
import re

import discord
from discord.ext import commands
from discord import app_commands

from core.overwatch_bot import OverwatchBot

class BoostCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        self.boost_channel = int(os.getenv("BOOST_MESSAGE_SEND_CHANNEL"))
        self.booster_channel = int(os.getenv("BOOSTER_EXCLUSIVE_CHANNEL", "1185662951043109008"))
        self.custom_roles: dict[int, int] = {}

    async def cog_load(self):
        guild = self.bot.get_guild(self.bot.guild_id)
        if not guild:
            return
        for member in guild.members:
            for role in member.roles:
                if role.name.startswith("Boost-"):
                    self.custom_roles[member.id] = role.id
                    break

    boost_group = app_commands.Group(name="부스트", description="서버 부스트 전용 기능")

    @boost_group.command(name="역할", description="부스트 기간 동안 사용할 개인 역할을 생성하거나 변경합니다.")
    @app_commands.describe(color="역할 색상 (#RRGGBB)")
    async def create_boost_role(self, interaction: discord.Interaction, color: str):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.premium_since:
            return await interaction.followup.send("서버 부스터 전용 명령어입니다.", ephemeral=True)

        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", color):
            return await interaction.followup.send("색상 코드는 #RRGGBB 형식이어야 합니다.", ephemeral=True)

        color_value = discord.Color(int(color.strip("#"), 16))

        guild = interaction.guild
        role_id = self.custom_roles.get(member.id)
        if role_id:
            role = guild.get_role(role_id)
            if role:
                await role.edit(color=color_value)
                await interaction.followup.send(f"{role.mention} 역할의 색상을 변경했습니다.", ephemeral=True)
                return
            else:
                self.custom_roles.pop(member.id, None)

        role = await guild.create_role(name=f"Boost-{member.display_name}", color=color_value, reason="부스터 개인 역할")
        await member.add_roles(role)
        self.custom_roles[member.id] = role.id
        await interaction.followup.send(f"개인 역할 {role.mention}을 생성했습니다.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.guild is None or before.guild.id != self.bot.guild_id:
            return

        if not before.premium_since and after.premium_since:
            channel = self.bot.get_channel(self.boost_channel)
            if channel:
                await channel.send(f"{after.mention}님, 서버를 부스트해주셔서 감사합니다! 🚀")
            booster_channel = self.bot.get_channel(self.booster_channel)
            if booster_channel:
                await booster_channel.send(f"{after.mention}님 환영합니다! `/부스트 역할` 명령으로 개인 역할을 설정하세요.")

        if before.premium_since and not after.premium_since:
            role_id = self.custom_roles.pop(after.id, None)
            if role_id:
                role = after.guild.get_role(role_id)
                if role:
                    try:
                        await after.remove_roles(role, reason="서버 부스트 종료")
                        await role.delete(reason="서버 부스트 종료")
                    except discord.Forbidden:
                        pass

async def setup(bot: OverwatchBot):
    await bot.add_cog(BoostCog(bot))

import os

import discord
from discord.ext import commands
from core.overwatch_bot import OverwatchBot

class BoostCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        self.boost_channel = int(os.getenv("BOOST_MESSAGE_SEND_CHANNEL"))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.guild is None or before.guild.id != self.bot.guild_id:
            return

        if not before.premium_since and after.premium_since:
            channel = self.bot.get_channel(self.boost_channel)  # 부스트 메시지를 보낼 채널 ID
            if channel:
                await channel.send(f"{after.mention}님, 서버를 부스트해주셔서 감사합니다! 🚀")

async def setup(bot: OverwatchBot):
    await bot.add_cog(BoostCog(bot))

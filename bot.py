import aiosqlite
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

from core import OverwatchBot

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = OverwatchBot(command_prefix='!', intents=intents, help_command=None)

if __name__ == '__main__':
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        raise ValueError('DISCORD_BOT_TOKEN 환경변수가 설정되어 있지 않습니다.')
    bot.run(token)
import discord
from discord.ext import commands

from core import OverwatchBot
import traceback

class ErrorHandlerCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            if hasattr(ctx, 'guild_check_failed') and ctx.guild_check_failed:
                await ctx.send("❌ 이 명령어는 O2G 서버에서만 사용할 수 있어요!")
            else:
                await ctx.send("❌ 명령어를 실행할 권한이 없습니다.")
            return
        elif isinstance(error, commands.CommandNotFound):
            return
        else:
            traceback.print_exc()
            print(f"[ERROR] Unhandled command error: {error}")
            await ctx.send("⚠️ 알 수 없는 오류가 발생했어요. 관리자에게 문의해주세요!")

async def setup(bot: OverwatchBot):
    await bot.add_cog(ErrorHandlerCog(bot))

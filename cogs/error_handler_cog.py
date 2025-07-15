import discord
from discord.ext import commands

from core import OverwatchBot
import traceback

class ErrorHandlerCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        bot.tree.error(coro = self.__dispatch_to_app_command_handler)

    async def __dispatch_to_app_command_handler(self, interaction: discord.Interaction,
                                                error: discord.app_commands.AppCommandError):
        self.bot.dispatch("app_command_error", interaction, error)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            hours, remainder = divmod(error.retry_after, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours >= 1:
                time_text = f"{int(hours)}시간"
            elif minutes >= 1:
                time_text = f"{int(minutes)}분"
            else:
                time_text = f"{int(seconds)}초"

            await interaction.response.send_message(
                f"이 명령어는 아직 사용할 수 없습니다. {time_text} 후에 다시 시도해주세요.",
                ephemeral=True
            )
        elif isinstance(error, discord.app_commands.CheckFailure):
            await interaction.response.send_message("명령어를 실행할 권한이 없습니다.", ephemeral=True)
        else:
            traceback.print_exc()
            print(f"[ERROR] Unhandled app command error: {error}")
            if interaction.response.is_done():
                await interaction.followup.send("⚠️ 알 수 없는 오류가 발생했어요. 관리자에게 문의해주세요!", ephemeral=True)
            else:
                await interaction.response.send_message("⚠️ 알 수 없는 오류가 발생했어요. 관리자에게 문의해주세요!", ephemeral=True)

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

import os

import discord
from discord.ext import commands
from discord import app_commands
from core.overwatch_bot import OverwatchBot

class ModerationCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        self.moderation_channel = int(os.getenv("MODERATION_MESSAGE_SEND_CHANNEL"))

    @app_commands.command(name="경고", description="유저에게 경고를 부여합니다.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.rename(target="대상", count="횟수", reason="사유")
    async def warn(self, interaction: discord.Interaction, target: discord.Member, count: int, reason: str):
        await self.bot.db.users.get_or_create_user(target.id, target.display_name)
        case_id = await self.bot.db.moderation.add_warning(target.id, interaction.user.id, reason, count)
        await interaction.response.send_message(f"{target.mention}에게 경고 {count}회를 부여했습니다. (사유: {reason})", ephemeral=True)

        log_channel = self.bot.get_channel(self.moderation_channel) # 로그 채널 ID
        if log_channel:
            embed = discord.Embed(title="경고 처분", color=discord.Color.orange())
            embed.add_field(name="대상", value=target.mention, inline=False)
            embed.add_field(name="관리자", value=interaction.user.mention, inline=False)
            embed.add_field(name="횟수", value=f"{count}회", inline=False)
            embed.add_field(name="사유", value=reason, inline=False)
            embed.set_footer(text=f"사건 ID: {case_id}")
            await log_channel.send(embed=embed)

    @app_commands.command(name="차단", description="유저를 서버에서 차단합니다.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.rename(target="대상", reason="사유")
    async def ban(self, interaction: discord.Interaction, target: discord.Member, reason: str):
        await self.bot.db.users.get_or_create_user(target.id, target.display_name)
        case_id = await self.bot.db.moderation.add_ban(target.id, interaction.user.id, reason)
        await target.ban(reason=reason)
        await interaction.response.send_message(f"{target.mention}님을 차단했습니다. (사유: {reason})", ephemeral=True)

        log_channel = self.bot.get_channel(self.moderation_channel) # 로그 채널 ID
        if log_channel:
            embed = discord.Embed(title="차단 처분", color=discord.Color.red())
            embed.add_field(name="대상", value=f"{target.mention} ({target.id})", inline=False)
            embed.add_field(name="관리자", value=interaction.user.mention, inline=False)
            embed.add_field(name="사유", value=reason, inline=False)
            embed.set_footer(text=f"사건 ID: {case_id}")
            await log_channel.send(embed=embed)

async def setup(bot: OverwatchBot):
    await bot.add_cog(ModerationCog(bot))

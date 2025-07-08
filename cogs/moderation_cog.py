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

    @app_commands.command(name="유저정보", description="유저의 상세 정보를 조회합니다.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def user_info(self, interaction: discord.Interaction, target: discord.Member):
        await interaction.response.defer(ephemeral=True)

        await self.bot.db.users.get_or_create_user(target.id, target.display_name)
        logs = await self.bot.db.moderation.get_user_logs(target.id)

        embed = discord.Embed(title=f"{target.display_name}님의 정보", color=target.color)
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)

        embed.add_field(name="닉네임", value=target.mention, inline=True)
        embed.add_field(name="고유번호 (ID)", value=target.id, inline=True)

        embed.add_field(name="디스코드 가입일", value=target.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="서버 가입일", value=target.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

        if logs:
            total_warnings = sum(log.count for log in logs if log.action == 'WARN' and log.count is not None)
            ban_count = sum(1 for log in logs if log.action == 'BAN')
            punishment_summary = f"경고 {total_warnings}회, 차단 {ban_count}회"

            log_text = ""
            for log in logs[:5]: # 최근 5개의 기록만 표시
                action = "경고" if log.action == 'WARN' else "차단"
                reason = log.reason or "사유 없음"
                count_text = f" ({log.count}회)" if log.action == 'WARN' and log.count else ""
                log_text += f"- **{action}{count_text}**: {reason} (ID: {log.case_id})\n"
            
            embed.add_field(name="처벌 요약", value=punishment_summary, inline=False)
            embed.add_field(name="최근 처벌 내역 (최대 5개)", value=log_text, inline=False)
        else:
            embed.add_field(name="처벌 내역", value="처벌 기록이 없습니다.", inline=False)

        await interaction.followup.send(embed=embed)

async def setup(bot: OverwatchBot):
    await bot.add_cog(ModerationCog(bot))

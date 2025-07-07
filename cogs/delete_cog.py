import os
import io

import discord
from discord.ext import commands
from discord import app_commands
import datetime
from pytz import timezone



class DeleteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.delete_message_send_channel = int(os.getenv('DELETE_MESSAGE_SEND_CHANNEL'))
        except (TypeError, ValueError):
            print("경고: DELETE_MESSAGE_SEND_CHANNEL 환경 변수가 설정되지 않았거나 잘못되었습니다.")
            self.delete_message_send_channel = None

    @commands.hybrid_command(name="삭제", description="메시지를 삭제하고, 삭제된 메시지 내용을 파일로 저장 및 전송합니다.")
    @app_commands.describe(개수="삭제할 메시지 개수 (1~100개)")
    @commands.has_permissions(manage_messages=True) # 명령어 실행에 '메시지 관리' 권한이 필요함을 명시
    @commands.bot_has_permissions(manage_messages=True) # 봇에게도 '메시지 관리' 권한이 필요함을 명시
    async def delete(self, ctx: commands.Context, 개수: int):
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
            send_method = ctx.interaction.followup.send # interaction.response.send_message
        else:
            send_method = ctx.send

        if not (1 <= 개수 <= 100):
            await send_method("1부터 100 사이의 숫자를 입력해주세요.")
            return

        try:
            deleted_messages = await ctx.channel.purge(limit=개수)

            if not deleted_messages:
                await send_method("삭제할 메시지가 없습니다.")
                return

            if not self.delete_message_send_channel:
                await send_method(f"{len(deleted_messages)}개의 메시지를 삭제했습니다. (로그 채널이 설정되지 않음)")
                return

            log_lines = []
            seoul_timezone = timezone("Asia/Seoul")
            for msg in reversed(deleted_messages):
                # [시간][유저ID][유저태그] 닉네임 : 내용
                log_line = (
                    f"[{msg.created_at.astimezone(seoul_timezone).strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"[{msg.author.id}][{msg.author}] {msg.author.display_name} : {msg.content}"
                )

                if msg.attachments:
                    for attachment in msg.attachments:
                        log_line += f"\n    [첨부파일: {attachment.url}]"

                log_lines.append(log_line)

            log_content = "\n".join(log_lines).encode('utf-8')
            log_file = io.BytesIO(log_content)

            filename = f"deleted_{ctx.channel.name}_{ctx.channel.id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file = discord.File(log_file, filename=filename)

            # 지정된 로그 채널 가져오기
            target_channel = self.bot.get_channel(self.delete_message_send_channel)

            if target_channel:
                await target_channel.send(
                    content=f"**{ctx.channel.mention}** 채널에서 **{ctx.author.mention}**님이 메시지 **{len(deleted_messages)}개**를 삭제했습니다.",
                    file=file
                )
                await send_method(f"{len(deleted_messages)}개의 메시지를 삭제하고, 내역을 로그 채널에 전송했습니다.")
            else:
                await send_method(f"로그 채널(ID: {self.delete_message_send_channel})을 찾을 수 없습니다. 메시지만 삭제되었습니다.")

        except discord.Forbidden:
            await send_method("봇에게 메시지를 삭제할 권한(Manage Messages)이 없습니다.")
        except Exception as e:
            await send_method(f"오류가 발생했습니다: {e}")
            print(f"삭제 명령어 실행 중 오류 발생: {e}")

async def setup(bot):
    await bot.add_cog(DeleteCog(bot)) 
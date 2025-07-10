import discord
from discord import app_commands, Interaction, TextChannel, Embed
from discord.ext import commands
from typing import Optional

from core.overwatch_bot import OverwatchBot
from core.local.repository.qna_repository import QnaRepository


class QnaCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        self.qna_repo: QnaRepository = self.bot.db.qna

    qna_command = app_commands.Group(name="질문", description="스레드를 생성해 Q&A를 편리하게 도와줍니다.",
                                    default_permissions=discord.Permissions(administrator=True))

    @qna_command.command(name="채널등록", description="유저 질문을 감지할 채널을 지정합니다.")
    @app_commands.describe(channel="질문 채널로 지정할 텍스트 채널")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def register_qna_channel(self, interaction: Interaction, channel: TextChannel):
        existing = await self.qna_repo.get_channel_by_id(channel.id)
        if existing:
            return await interaction.response.send_message(f"{channel.mention} 채널은 이미 질문 채널로 등록되어 있습니다.", ephemeral=True)

        await self.qna_repo.add_channel(channel.id, interaction.guild.id)
        await interaction.response.send_message(f"{channel.mention} 채널을 질문 채널로 등록했습니다.", ephemeral=True)

    @qna_command.command(name="채널해제", description="해당 채널의 질문 자동화 기능을 비활성화합니다.")
    @app_commands.describe(channel="질문 채널에서 해제할 텍스트 채널")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def unregister_qna_channel(self, interaction: Interaction, channel: TextChannel):
        removed = await self.qna_repo.remove_channel(channel.id)
        if removed:
            await interaction.response.send_message(f"{channel.mention} 채널을 질문 채널에서 해제했습니다.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{channel.mention} 채널은 질문 채널로 등록되어 있지 않습니다.", ephemeral=True)

    @qna_command.command(name="고정설정", description="지정 채널에 항상 유지될 고정 안내 메시지를 설정합니다.")
    @app_commands.describe(channel="고정 메시지를 설정할 채널", title="메시지 제목", content="메시지 내용")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def set_pinned_message(self, interaction: Interaction, channel: TextChannel, title: str, content: str):
        qna_channel = await self.qna_repo.get_channel_by_id(channel.id)
        if not qna_channel:
            return await interaction.response.send_message(f"{channel.mention} 채널은 질문 채널로 먼저 등록해야 합니다.", ephemeral=True)

        # Delete previous pinned message if it exists
        if qna_channel.pinned_message_id:
            try:
                msg = await channel.fetch_message(qna_channel.pinned_message_id)
                await msg.delete()
            except discord.NotFound:
                pass  # Message already deleted

        embed = Embed(title=title, description=content, color=discord.Color.blue())
        new_message = await channel.send(embed=embed)

        await self.qna_repo.update_pinned_message(channel.id, new_message.id, title, content)
        await interaction.response.send_message(f"{channel.mention} 채널에 고정 메시지를 설정했습니다.", ephemeral=True)

    @qna_command.command(name="고정삭제", description="고정 안내 메시지를 제거합니다.")
    @app_commands.describe(channel="고정 메시지를 삭제할 채널")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def delete_pinned_message(self, interaction: Interaction, channel: TextChannel):
        qna_channel = await self.qna_repo.get_channel_by_id(channel.id)
        if not qna_channel or not qna_channel.pinned_message_id:
            return await interaction.response.send_message(f"{channel.mention} 채널에 설정된 고정 메시지가 없습니다.", ephemeral=True)

        try:
            msg = await channel.fetch_message(qna_channel.pinned_message_id)
            await msg.delete()
        except discord.NotFound:
            pass  # Message already deleted

        await self.qna_repo.remove_pinned_message(channel.id)
        await interaction.response.send_message(f"{channel.mention} 채널의 고정 메시지를 삭제했습니다.", ephemeral=True)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None or message.guild.id != self.bot.guild_id:
            return

        # Case 1: Message is in a thread within a QnA channel
        if isinstance(message.channel, discord.Thread):
            qna_channel = await self.qna_repo.get_channel_by_id(message.channel.parent_id)
            if qna_channel:
                if message.content == "!해결":
                    is_author = message.author.id == message.channel.owner_id
                    has_perms = message.author.guild_permissions.manage_messages

                    if is_author or has_perms:
                        await message.channel.send("✅ 질문이 해결 처리되었습니다!")
                        await message.channel.edit(name=f"[해결됨] {message.channel.name}")
                    else:
                        await message.author.send("스레드 작성자 또는 관리자만 해결 처리할 수 있습니다.", delete_after=10)
                return # Stop processing after handling thread command

        # Case 2: Message is in a QnA channel
        qna_channel = await self.qna_repo.get_channel_by_id(message.channel.id)
        if not qna_channel:
            return

        # Repost pinned message if needed
        if qna_channel.pinned_message_id and qna_channel.pinned_title:
            try:
                # Check if the last message is the pinned one
                async for last_message in message.channel.history(limit=1):
                    if last_message.id != qna_channel.pinned_message_id:
                        # If not, delete old and repost
                        old_msg = await message.channel.fetch_message(qna_channel.pinned_message_id)
                        await old_msg.delete()
                        embed = Embed(title=qna_channel.pinned_title, description=qna_channel.pinned_content, color=discord.Color.blue())
                        new_msg = await message.channel.send(embed=embed)
                        await self.qna_repo.update_pinned_message(message.channel.id, new_msg.id, qna_channel.pinned_title, qna_channel.pinned_content)
            except (discord.NotFound, discord.Forbidden):
                # Pinned message was deleted manually, just repost
                embed = Embed(title=qna_channel.pinned_title, description=qna_channel.pinned_content, color=discord.Color.blue())
                new_msg = await message.channel.send(embed=embed)
                await self.qna_repo.update_pinned_message(message.channel.id, new_msg.id, qna_channel.pinned_title, qna_channel.pinned_content)

        # Create a thread for the user's question
        # To prevent creating a thread for the bot's own pinned message repost
        if message.author.id != self.bot.user.id:
            thread = await message.create_thread(name=f"[{message.author.display_name}]님의 디코 질문")
            await thread.send("✅ 질문이 등록되었습니다!\n해결되었다면 `!해결` 명령어를 사용해 질문을 닫아주세요.")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None or message.guild.id != self.bot.guild_id:
            return

        qna_channel = await self.qna_repo.get_channel_by_id(message.channel.id)
        if qna_channel and qna_channel.pinned_message_id == message.id:
            # Pinned message was deleted, repost it.
            try:
                embed = Embed(title=qna_channel.pinned_title, description=qna_channel.pinned_content, color=discord.Color.blue())
                new_msg = await message.channel.send(embed=embed)
                await self.qna_repo.update_pinned_message(message.channel.id, new_msg.id, qna_channel.pinned_title, qna_channel.pinned_content)
            except discord.Forbidden:
                pass # Can't send message, probably permissions issue


async def setup(bot: OverwatchBot):
    await bot.add_cog(QnaCog(bot))

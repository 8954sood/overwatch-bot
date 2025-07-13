import discord
from discord.ext import commands, tasks
from discord import app_commands
import re
from core.overwatch_bot import OverwatchBot

class AutoVcCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        self.managed_channels = set() # 메모리에 자동 생성된 채널 ID를 캐싱

    async def cog_load(self):
        """Cog가 로드될 때 (봇 시작 시) 데이터베이스에서 상태를 복원합니다."""
        all_managed_ids = await self.bot.db.auto_vc.get_all_managed_channels()
        self.managed_channels = set(all_managed_ids)
        print(f"[AutoVC] {len(self.managed_channels)}개의 관리 채널 정보를 DB에서 복원했습니다.")
        self.cleanup_check.start()

    def cog_unload(self):
        """Cog가 언로드될 때 (봇 종료 또는 리로드 시) 루프를 중지합니다."""
        self.cleanup_check.cancel()

    @tasks.loop(minutes=10)
    async def cleanup_check(self):
        """주기적으로 DB와 실제 채널 상태를 동기화합니다."""
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()

        all_managed_ids = list(self.managed_channels)
        for channel_id in all_managed_ids:
            try:
                channel = await self.bot.fetch_channel(channel_id)
                if isinstance(channel, discord.VoiceChannel) and not any(m for m in channel.members if not m.bot):
                    await channel.delete(reason="주기적인 자동 생성 채널 정리")
                    await self.remove_channel_from_db(channel.id)
            except discord.NotFound:
                await self.remove_channel_from_db(channel_id)
            except Exception as e:
                print(f"[AutoVC Cleanup] 채널 정리 중 오류 발생 (ID: {channel_id}): {e}")

    auto_vc_commands = app_commands.Group(name="자동통화방", description="자동 생성 통화방과 관련된 명령어입니다.",
                                    default_permissions=discord.Permissions(administrator=True))

    @auto_vc_commands.command(name="설정", description="자동 생성 통화방을 설정합니다.")
    @app_commands.rename(generator_channel="생성기채널", category="생성될카테고리", base_name="채널이름")
    async def setup_auto_vc(self, interaction: discord.Interaction, generator_channel: discord.VoiceChannel, category: discord.CategoryChannel, base_name: str):
        await self.bot.db.auto_vc.add_generator(generator_channel.id, category.id, base_name, interaction.guild.id)
        await interaction.response.send_message(f"자동 통화방이 설정되었습니다: {generator_channel.mention}에 접속하면 -> {category.name}에 `{base_name} N` 채널이 생성됩니다.", ephemeral=True)

    @auto_vc_commands.command(name="삭제", description="자동 생성 통화방 설정을 삭제합니다.")
    @app_commands.rename(generator_channel="설정된_생성기채널")
    async def remove_auto_vc(self, interaction: discord.Interaction, generator_channel: discord.VoiceChannel):
        await self.bot.db.auto_vc.remove_generator(generator_channel.id)
        await interaction.response.send_message(f"자동 통화방 설정이 삭제되었습니다: {generator_channel.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.guild is None or member.guild.id != self.bot.guild_id:
            return

        if after.channel:
            generator = await self.bot.db.auto_vc.get_generator(after.channel.id)
            if generator:
                await self._create_and_move_user(member, generator)

        if before.channel and before.channel.id in self.managed_channels:
            if not any(m for m in before.channel.members if not m.bot):
                try:
                    await before.channel.delete(reason="자동 생성 채널 정리")
                    await self.remove_channel_from_db(before.channel.id)
                except discord.NotFound:
                    await self.remove_channel_from_db(before.channel.id)
                except Exception as e:
                    print(f"[AutoVC] 채널 삭제 중 오류 발생: {e}")

    async def _create_and_move_user(self, member: discord.Member, generator_config):
        guild = member.guild
        category = guild.get_channel(generator_config.category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            return

        managed_channels = []
        for ch in category.voice_channels:
            if ch.id in self.managed_channels and ch.name.startswith(generator_config.base_name):
                match = re.search(r'(\d+)$', ch.name)
                if match:
                    managed_channels.append((int(match.group(1)), ch))

        managed_channels.sort(key=lambda x: x[0])
        existing_numbers = {num for num, _ in managed_channels}

        new_number = 1
        while new_number in existing_numbers:
            new_number += 1

        new_channel_name = f"{generator_config.base_name} {new_number}"

        # ✅ 채널 배치 계산 방식 교체
        insert_index = 0
        for i, (num, _) in enumerate(managed_channels):
            if new_number < num:
                break
            insert_index = i + 1

        if managed_channels:
            if insert_index == 0:
                position = managed_channels[0][1].position - 1
            else:
                position = managed_channels[insert_index - 1][1].position + 1
        else:
            position = category.position - 1

        overwrites = {member: discord.PermissionOverwrite(manage_channels=True, manage_roles=True)}

        try:
            new_channel = await category.create_voice_channel(
                new_channel_name,
                overwrites=overwrites,
                position=position,
                user_limit=5,  # 기본 인원 제한 5명
                reason=f"{member.display_name}의 요청으로 자동 생성"
            )
            await self.add_channel_to_db(new_channel.id, member.id, guild.id, generator_config.generator_channel_id)
            await member.move_to(new_channel)
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"자동 통화방 생성 실패: {e}")

    async def add_channel_to_db(self, channel_id: int, owner_id: int, guild_id: int, generator_id: int):
        await self.bot.db.auto_vc.add_managed_channel(channel_id, owner_id, guild_id, generator_id)
        self.managed_channels.add(channel_id)

    async def remove_channel_from_db(self, channel_id: int):
        await self.bot.db.auto_vc.remove_managed_channel(channel_id)
        self.managed_channels.discard(channel_id)

    # --- User Commands ---
    vc = app_commands.Group(name="통화방", description="현재 속한 통화방을 관리합니다.")

    @vc.command(name="이름", description="통화방의 이름을 변경합니다.")
    @app_commands.describe(새이름="새로운 채널 이름")
    async def change_channel_name(self, interaction: discord.Interaction, 새이름: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("음성 채널에 먼저 참여해주세요.", ephemeral=True)

        channel = interaction.user.voice.channel
        owner_id = await self.bot.db.auto_vc.get_channel_owner(channel.id)

        if owner_id != interaction.user.id:
            return await interaction.response.send_message("채널 소유자만 이름을 변경할 수 있습니다.", ephemeral=True)

        try:
            await channel.edit(name=새이름)
            await interaction.response.send_message(f"채널 이름이 '{새이름}'(으)로 변경되었습니다.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("채널 이름을 변경할 권한이 없습니다.", ephemeral=True)

    @vc.command(name="인원", description="통화방의 최대 인원을 변경합니다.")
    @app_commands.describe(인원="새로운 최대 인원 (1-99)")
    async def change_channel_limit(self, interaction: discord.Interaction, 인원: app_commands.Range[int, 1, 99]):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("음성 채널에 먼저 참여해주세요.", ephemeral=True)

        channel = interaction.user.voice.channel
        owner_id = await self.bot.db.auto_vc.get_channel_owner(channel.id)

        if owner_id != interaction.user.id:
            return await interaction.response.send_message("채널 소유자만 인원을 변경할 수 있습니다.", ephemeral=True)

        try:
            await channel.edit(user_limit=인원)
            await interaction.response.send_message(f"채널 최대 인원이 {인원}명으로 변경되었습니다.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("채널 인원을 변경할 권한이 없습니다.", ephemeral=True)


async def setup(bot: OverwatchBot):
    await bot.add_cog(AutoVcCog(bot))
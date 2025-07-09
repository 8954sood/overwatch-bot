from typing import Optional

import discord
from discord import app_commands, Interaction, Embed, Role
from discord.app_commands import Choice
from discord.ext import commands

from core.local.repository.role_message_repository import RoleMessageRepository
from core.model.role_message_models import RoleButton, RoleMessage
from core.overwatch_bot import OverwatchBot
from view import RoleButtonView

DEFAULT_COLOR = discord.Color.blue()

def parse_color(color_hex: str) -> Optional[discord.Color]:
    if not color_hex:
        return None
    try:
        return discord.Color(int(color_hex.strip('#'), 16))
    except ValueError:
        return None

class RoleMessageCog(commands.Cog, name="역할메시지"):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        self.role_message_repo: RoleMessageRepository = self.bot.db.role_message_repo

    @commands.Cog.listener()
    async def on_ready(self):
        all_messages = await self.role_message_repo.get_all()
        for msg_data in all_messages:
            self.bot.add_view(RoleButtonView(self.bot, msg_data.buttons), message_id=msg_data.message_id)

    role_group = app_commands.Group(name="역할", description="역할 부여 메시지 관련 명령어")

    @role_group.command(name="메시지생성", description="현재 채널에 역할 메시지를 생성합니다.")
    @app_commands.describe(content="역할 메시지의 내용을 입력합니다.", color="임베드 색상을 헥스 코드로 입력합니다. (예: #FF0000)")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.rename(content="내용", color="색상")
    async def create_message(self, interaction: Interaction, content: str, color: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        if await self.role_message_repo.get_by_channel_id(interaction.channel_id):
            await interaction.followup.send("이 채널에는 이미 역할 메시지가 존재합니다.", ephemeral=True)
            return

        color_obj = parse_color(color) if color else DEFAULT_COLOR
        if color and color_obj is None:
            await interaction.followup.send("유효하지 않은 색상 코드입니다. 헥스 코드(#RRGGBB) 형식을 확인해주세요.", ephemeral=True)
            return

        embed = Embed(description=content, color=color_obj)
        view = RoleButtonView(self.bot, [])
        message = await interaction.channel.send(embed=embed, view=view)

        await self.role_message_repo.create_role_message(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            message_id=message.id,
            content=content,
            color=color or f'#{DEFAULT_COLOR.value:06X}'
        )
        await interaction.followup.send("역할 메시지를 생성했습니다.", ephemeral=True)

    @role_group.command(name="메시지수정", description="역할 메시지의 내용이나 색상을 수정합니다.")
    @app_commands.describe(content="새로운 메시지 내용", color="새로운 임베드 색상 (헥스 코드) #000000")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.rename(content="내용", color="색상")
    async def edit_message(self, interaction: Interaction, content: Optional[str] = None, color: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        if content is None and color is None:
            await interaction.followup.send("수정할 내용이나 색상 중 하나는 입력해야 합니다.", ephemeral=True)
            return

        role_message = await self.role_message_repo.get_by_channel_id(interaction.channel_id)
        if not role_message:
            await interaction.followup.send("이 채널에 역할 메시지가 존재하지 않습니다.", ephemeral=True)
            return

        if color and parse_color(color) is None:
            await interaction.followup.send("유효하지 않은 색상 코드입니다. 헥스 코드(#RRGGBB) 형식을 확인해주세요.", ephemeral=True)
            return

        new_content = content or role_message.content
        new_color_hex = color or role_message.color

        await self.role_message_repo.update_message(interaction.channel_id, new_content, new_color_hex)
        role_message.content = new_content
        role_message.color = new_color_hex

        await self._update_message(role_message)
        await interaction.followup.send("역할 메시지를 수정했습니다.", ephemeral=True)

    @role_group.command(name="메시지삭제", description="현재 채널의 역할 메시지를 삭제합니다.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def delete_message(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        role_message = await self.role_message_repo.get_by_channel_id(interaction.channel_id)
        if not role_message:
            await interaction.followup.send("이 채널에 역할 메시지가 존재하지 않습니다.", ephemeral=True)
            return

        try:
            message = await interaction.channel.fetch_message(role_message.message_id)
            await message.delete()
        except discord.NotFound:
            pass  # 메시지가 이미 삭제됨
        except discord.Forbidden:
            await interaction.followup.send("메시지를 삭제할 권한이 없습니다.", ephemeral=True)
            return

        await self.role_message_repo.delete_role_message(interaction.channel_id)
        await interaction.followup.send("역할 메시지를 삭제했습니다.", ephemeral=True)

    @role_group.command(name="역할추가", description="역할 메시지에 역할 버튼을 추가합니다.")
    @app_commands.describe(role="추가할 역할", label="버튼에 표시될 텍스트", emoji="버튼에 표시될 이모지", color="버튼에 사용될 색상")
    @app_commands.choices(color=[
        Choice(name="파랑", value="primary"),
        Choice(name="회색", value="secondary"),
        Choice(name="초록", value="success"),
        Choice(name="빨강", value="danger"),
    ])
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.rename(role="역할", label="라벨", emoji="이모지", color="색상")
    async def add_role(self, interaction: Interaction, role: Role, label: Optional[str] = None, emoji: Optional[str] = None, color: Optional[Choice[str]] = None):
        await interaction.response.defer(ephemeral=True)
        if label is None and emoji is None:
            await interaction.followup.send("버튼 라벨이나 이모지 중 하나는 반드시 입력해야 합니다.", ephemeral=True)
            return

        role_message = await self.role_message_repo.get_by_channel_id(interaction.channel_id)
        if not role_message:
            await interaction.followup.send("먼저 `/역할 메시지생성` 명령어로 메시지를 생성해주세요.", ephemeral=True)
            return

        if any(b.role_id == role.id for b in role_message.buttons):
            await interaction.followup.send("이미 해당 역할이 버튼으로 존재합니다.", ephemeral=True)
            return

        button_style = color.value if color else 'secondary'
        new_button = RoleButton(role_id=role.id, label=label, emoji=emoji, style=button_style)
        role_message.buttons.append(new_button)
        await self.role_message_repo.update_buttons(interaction.channel_id, role_message.buttons)

        await self._update_message(role_message)
        await interaction.followup.send(f"'{role.name}' 역할 버튼을 추가했습니다.", ephemeral=True)

    @role_group.command(name="역할삭제", description="역할 메시지에서 역할 버튼을 제거합니다.")
    @app_commands.describe(role="제거할 역할")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.rename(role="역할")
    async def remove_role(self, interaction: Interaction, role: Role):
        await interaction.response.defer(ephemeral=True)
        role_message = await self.role_message_repo.get_by_channel_id(interaction.channel_id)
        if not role_message:
            await interaction.followup.send("이 채널에 역할 메시지가 존재하지 않습니다.", ephemeral=True)
            return

        original_button_count = len(role_message.buttons)
        role_message.buttons = [b for b in role_message.buttons if b.role_id != role.id]

        if len(role_message.buttons) == original_button_count:
            await interaction.followup.send("해당 역할 버튼을 찾을 수 없습니다.", ephemeral=True)
            return

        await self.role_message_repo.update_buttons(interaction.channel_id, role_message.buttons)
        await self._update_message(role_message)
        await interaction.followup.send(f"'{role.name}' 역할 버튼을 제거했습니다.", ephemeral=True)

    async def _update_message(self, role_message_data: RoleMessage):
        channel = self.bot.get_channel(role_message_data.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(role_message_data.message_id)
            color_obj = parse_color(role_message_data.color) or DEFAULT_COLOR
            embed = Embed(description=role_message_data.content, color=color_obj)
            view = RoleButtonView(self.bot, role_message_data.buttons)
            await message.edit(embed=embed, view=view)
        except discord.NotFound:
            await self.role_message_repo.delete_role_message(role_message_data.channel_id)
        except discord.Forbidden:
            pass


async def setup(bot: OverwatchBot):
    await bot.add_cog(RoleMessageCog(bot))

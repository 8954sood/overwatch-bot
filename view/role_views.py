import discord
from discord import Interaction

from core import OverwatchBot
from core.model import RoleButton

BUTTON_STYLES = {
    'primary': discord.ButtonStyle.primary,
    'secondary': discord.ButtonStyle.secondary,
    'success': discord.ButtonStyle.success,
    'danger': discord.ButtonStyle.danger,
}

class RoleButtonView(discord.ui.View):
    def __init__(self, bot: OverwatchBot, buttons: list[RoleButton]):
        super().__init__(timeout=None)
        self.bot = bot
        for button_data in buttons:
            self.add_item(self.RoleToggleButton(bot, button_data))

    class RoleToggleButton(discord.ui.Button):
        def __init__(self, bot: OverwatchBot, button_data: RoleButton):
            style = BUTTON_STYLES.get(button_data.style, discord.ButtonStyle.secondary)
            super().__init__(
                label=button_data.label,
                emoji=button_data.emoji,
                style=style,
                custom_id=f"role_toggle:{button_data.role_id}"
            )
            self.bot = bot
            self.role_id = button_data.role_id

        async def callback(self, interaction: Interaction):
            await interaction.response.defer(ephemeral=True)
            role = interaction.guild.get_role(self.role_id)
            if not role:
                await interaction.followup.send("역할을 찾을 수 없습니다. 관리자에게 문의하세요.", ephemeral=True)
                return

            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.followup.send(f"'{role.name}' 역할이 제거되었습니다.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.followup.send(f"'{role.name}' 역할이 부여되었습니다.", ephemeral=True)

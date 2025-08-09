import discord
from core.model import ShopItem

class ItemSelectView(discord.ui.View):
    def __init__(self, items: list[ShopItem], select_callback):
        super().__init__(timeout=30)
        self.select_callback = select_callback
        options = [
            discord.SelectOption(label=item.name, value=str(item.id), emoji=item.emoji)
            for item in items
        ]
        self.add_item(ItemSelect(options))

class ItemSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="아이템을 선택하세요.", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.view.select_callback(interaction, int(self.values[0]))


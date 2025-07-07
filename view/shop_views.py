import discord
from core.model import ShopItem
from core.utiles import money_to_string


class ShopView(discord.ui.View):
    def __init__(self, shop_items: list[ShopItem], purchase_callback):
        super().__init__(timeout=180)
        self.purchase_callback = purchase_callback

        options = []
        for item in shop_items:
            label = f"{item.name}"
            if item.item_type == "ROLE" and item.duration_days and item.duration_days > 0:
                label += f" ({item.duration_days}일)"

            options.append(discord.SelectOption(
                label=label,
                value=str(item.id),
                description=f"[{item.item_type}] {money_to_string(item.price)}",
                emoji=item.emoji
            ))

        # Select 메뉴가 비어있으면 추가하지 않음
        if options:
            self.add_item(ShopSelect(options))


class ShopSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="구매할 상품을 선택하세요.", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.view.purchase_callback(interaction, int(self.values[0]))
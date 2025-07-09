import discord
from discord import app_commands
from discord.ext import commands
import datetime

from core import OverwatchBot
from core.utiles import money_to_string
from view import ShopView


class ShopCog(commands.Cog, name="상점"):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot

    async def purchase_callback(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)
        item = await self.bot.db.shop.get_item_by_id(item_id)
        if not item:
            return await interaction.followup.send("존재하지 않는 상품입니다.", ephemeral=True)

        user = await self.bot.db.users.get_or_create_user(interaction.user.id, interaction.user.display_name)
        if user.balance < item.price:
            return await interaction.followup.send("잔고가 부족합니다.", ephemeral=True)

        # 구매 처리
        await self.bot.db.users.update_balance(user.user_id, -item.price)

        if item.item_type == "ITEM":
            await self.bot.db.shop.add_to_inventory(user.user_id, item.id)
            message = f"아이템 **{item.name}**을(를) 구매하여 인벤토리에 추가했습니다."

        elif item.item_type == "ROLE":
            role = interaction.guild.get_role(item.role_id)
            if not role:
                # 롤백
                await self.bot.db.users.update_balance(user.user_id, item.price)
                return await interaction.followup.send("역할을 찾을 수 없어 구매를 취소합니다.", ephemeral=True)

            try:
                await interaction.user.add_roles(role)
            except discord.Forbidden:
                await self.bot.db.users.update_balance(user.user_id, item.price)
                return await interaction.followup.send("역할을 부여할 권한이 없습니다.", ephemeral=True)

            message = f"역할 **{role.name}**을(를) 구매하여 부여받았습니다."
            if item.duration_days and item.duration_days > 0:
                expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=item.duration_days)
                await self.bot.db.shop.add_temporary_role(user.user_id, role.id, expires_at.isoformat())
                message += f"\n이 역할은 **{item.duration_days}일** 후에 만료됩니다."

        await interaction.followup.send(message, ephemeral=True)
        # 상점 메시지 업데이트 (선택사항: 구매 후 목록을 비활성화)
        # view = ShopView([], self.purchase_callback)
        # view.stop()
        # await interaction.message.edit(view=view)

    @app_commands.command(name="상점", description="구매 가능한 아이템 및 역할 목록을 봅니다.")
    async def shop(self, interaction: discord.Interaction):
        user = await self.bot.db.users.get_or_create_user(interaction.user.id, interaction.user.display_name)
        items = await self.bot.db.shop.get_all_items()
        if not items:
            return await interaction.response.send_message("상점에 등록된 상품이 없습니다.", ephemeral=True)

        embed = discord.Embed(title="🛒 상점", description="아래 목록에서 구매할 상품을 선택하세요.",
                              color=discord.Color.from_rgb(255, 204, 77))
        embed.add_field(name="잔액", value=money_to_string(user.balance))
        view = ShopView(items, self.purchase_callback)
        await interaction.response.send_message(embed=embed, view=view)

    # --- 상점 관리 명령어 그룹 ---
    shop_admin = app_commands.Group(name="상점관리", description="상점 상품을 관리합니다.",
                                    default_permissions=discord.Permissions(administrator=True))

    @shop_admin.command(name="역할추가", description="상점에 판매할 역할을 추가합니다.")
    @app_commands.describe(역할="판매할 역할", 가격="역할의 가격", 기간="역할 유지 기간 (일, 0은 영구)", 이모지="표시할 이모지")
    async def add_role(self, interaction: discord.Interaction, 역할: discord.Role, 가격: app_commands.Range[int, 0],
                       기간: app_commands.Range[int, 0], 이모지: str = None):
        await self.bot.db.shop.add_item(
            item_type="ROLE",
            name=역할.name,
            price=가격,
            duration_days=기간,
            role_id=역할.id,
            emoji=이모지
        )
        await interaction.response.send_message(f"역할 '{역할.name}'을(를) 상점에 추가했습니다.", ephemeral=True)

    @shop_admin.command(name="아이템추가", description="상점에 판매할 아이템을 추가합니다.")
    @app_commands.describe(이름="판매할 아이템 이름", 가격="아이템 가격", 이모지="표시할 이모지")
    async def add_item(self, interaction: discord.Interaction, 이름: str, 가격: app_commands.Range[int, 0],
                       이모지: str = None):
        await self.bot.db.shop.add_item(
            item_type="ITEM",
            name=이름,
            price=가격,
            emoji=이모지
        )
        await interaction.response.send_message(f"아이템 '{이름}'을(를) 상점에 추가했습니다.", ephemeral=True)

    @shop_admin.command(name="삭제", description="상점에서 상품을 삭제합니다.")
    @app_commands.describe(상품이름="삭제할 상품의 정확한 이름")
    async def remove_item(self, interaction: discord.Interaction, 상품이름: str):
        success = await self.bot.db.shop.remove_item_by_name(상품이름)
        if success:
            await interaction.response.send_message(f"상품 '{상품이름}'을(를) 상점에서 삭제했습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("해당 이름의 상품을 찾을 수 없습니다.", ephemeral=True)


async def setup(bot: OverwatchBot):
    await bot.add_cog(ShopCog(bot))

import traceback

import discord
from discord import app_commands
from discord.ext import commands
import datetime

from core import OverwatchBot
from core.utiles import money_to_string
from view import ShopView, NicknameChangeModal


class ShopCog(commands.Cog, name="상점"):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        try:
            self.log_channel_id = int(os.getenv("SHOP_LOG_CHANNEL"))
        except (TypeError, ValueError):
            self.log_channel_id = None

    async def log_purchase(self, member: discord.Member, item_name: str, price: int):
        if not self.log_channel_id:
            return
        channel = self.bot.get_channel(self.log_channel_id)
        if not channel:
            return
        embed = discord.Embed(title="구매 로그", color=discord.Color.blue())
        embed.add_field(name="구매자", value=member.mention, inline=False)
        embed.add_field(name="상품", value=item_name, inline=False)
        embed.add_field(name="가격", value=money_to_string(price), inline=False)
        await channel.send(embed=embed)

    async def purchase_callback(self, interaction: discord.Interaction, item_id: int):
        item = await self.bot.db.shop.get_item_by_id(item_id)
        if not item:
            return await interaction.response.send_message("존재하지 않는 상품입니다.", ephemeral=True)

        user = await self.bot.db.users.get_or_create_user(interaction.user.id, interaction.user.display_name)
        if user.balance < item.price:
            return await interaction.response.send_message("잔고가 부족합니다.", ephemeral=True)

        # 구매 처리
        await self.bot.db.users.update_balance(user.user_id, -item.price)

        if item.item_type == "ITEM":
            await self.bot.db.shop.add_to_inventory(user.user_id, item.id)
            message = f"아이템 **{item.name}**을(를) 구매하여 인벤토리에 추가했습니다."
            await interaction.response.send_message(message, ephemeral=True)
            await self.log_purchase(interaction.user, item.name, item.price)

        elif item.item_type == "ROLE":
            role = interaction.guild.get_role(item.role_id)
            if not role:
                await self.bot.db.users.update_balance(user.user_id, item.price)
                return await interaction.response.send_message("역할을 찾을 수 없어 구매를 취소합니다.", ephemeral=True)

            try:
                await interaction.user.add_roles(role)
            except discord.Forbidden:
                await self.bot.db.users.update_balance(user.user_id, item.price)
                return await interaction.response.send_message("역할을 부여할 권한이 없습니다.", ephemeral=True)

            message = f"역할 **{role.name}**을(를) 구매하여 부여받았습니다."
            if item.duration_days and item.duration_days > 0:
                expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=item.duration_days)
                await self.bot.db.shop.add_temporary_role(user.user_id, role.id, expires_at.isoformat())
                message += f"\n이 역할은 **{item.duration_days}일** 후에 만료됩니다."
            await interaction.response.send_message(message, ephemeral=True)
            await self.log_purchase(interaction.user, role.name, item.price)

        elif item.item_type == "NICKNAME_CHANGE":

            async def nickname_callback(modal_interaction, new_nickname):
                try:
                    await modal_interaction.user.edit(nick=new_nickname)
                    await self.bot.db.users.update_display_name(user.user_id, new_nickname)
                    await modal_interaction.response.send_message(f"닉네임을 성공적으로 '{new_nickname}'(으)로 변경했습니다.", ephemeral=True)
                    await self.log_purchase(modal_interaction.user, "닉네임 변경권", item.price)
                except discord.Forbidden:
                    await self.bot.db.users.update_balance(user.user_id, item.price)  # 롤백
                    await modal_interaction.response.send_message("닉네임을 변경할 권한이 없습니다.", ephemeral=True)
                except discord.HTTPException as e:
                    await self.bot.db.users.update_balance(user.user_id, item.price)  # 롤백
                    await modal_interaction.response.send_message(f"닉네임 변경 중 오류가 발생했습니다: {e}", ephemeral=True)

            modal = NicknameChangeModal(nickname_callback)
            await interaction.response.send_modal(modal)
        
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
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # --- 상점 관리 명령어 그룹 ---
    shop_admin = app_commands.Group(name="상점관리", description="상점 상품을 관리합니다.",
                                    default_permissions=discord.Permissions(administrator=True))

    @shop_admin.command(name="역할추가", description="상점에 판매할 역할을 추가합니다.")
    @app_commands.describe(역할="판매할 역할", 가격="역할의 가격", 기간="역할 유지 기간 (일, 0은 영구)", 이모지="표시할 이모지")
    async def add_role(self, interaction: discord.Interaction, 역할: discord.Role, 가격: app_commands.Range[int, 0],
                       기간: app_commands.Range[int, 0], 이모지: str = None):
        try:
            if not self.bot.db.shop.get_item_by_name(역할.name) is None:
                return await interaction.response.send_message(f"중복된 이름의 아이템이 상점에 존재합니다.")
            await self.bot.db.shop.add_item(
                item_type="ROLE",
                name=역할.name,
                price=가격,
                duration_days=기간,
                role_id=역할.id,
                emoji=이모지
            )
            await interaction.response.send_message(f"역할 '{역할.name}'을(를) 상점에 추가했습니다.", ephemeral=True)
        except Exception as E:
            traceback.print_exc()
            await interaction.response.send_message(f"아이템 추가에 실패했습니다.\n사유 : ${E}", ephemeral=True)


    @shop_admin.command(name="아이템추가", description="상점에 판매할 아이템을 추가합니다.")
    @app_commands.describe(이름="판매할 아이템 이름", 가격="아이템 가격", 이모지="표시할 이모지")
    async def add_item(self, interaction: discord.Interaction, 이름: str, 가격: app_commands.Range[int, 0],
                       이모지: str = None):
        try:
            if not self.bot.db.shop.get_item_by_name(이름) is None:
                return await interaction.response.send_message(f"중복된 이름의 아이템이 상점에 존재합니다.")
            await self.bot.db.shop.add_item(
                item_type="ITEM",
                name=이름,
                price=가격,
                emoji=이모지
            )
            await interaction.response.send_message(f"아이템 '{이름}'을(를) 상점에 추가했습니다.", ephemeral=True)
        except Exception as E:
            traceback.print_exc()
            await interaction.response.send_message(f"아이템 추가에 실패했습니다.\n사유 : ${E}", ephemeral=True)

    @shop_admin.command(name="닉네임변경권추가", description="상점에 닉네임 변경권을 추가합니다.")
    @app_commands.describe(가격="변경권의 가격", 이모지="표시할 이모지")
    async def add_nickname_change_item(self, interaction: discord.Interaction, 가격: app_commands.Range[int, 0],
                                       이모지: str = None):
        if not self.bot.db.shop.get_item_by_name("닉네임 변경권") is None:
            return await interaction.response.send_message(f"닉네임 변경권 아이템이 이미 상점에 존재합니다.")
        await self.bot.db.shop.add_item(
            item_type="NICKNAME_CHANGE",
            name="닉네임 변경권",
            price=가격,
            emoji=이모지
        )
        await interaction.response.send_message("'닉네임 변경권'을(를) 상점에 추가했습니다.", ephemeral=True)

    async def item_name_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        items = await self.bot.db.shop.get_all_items()
        choices = [
            app_commands.Choice(name=item.name, value=item.name)
            for item in items if current.lower() in item.name.lower()
        ]
        return choices[:25]

    @shop_admin.command(name="삭제", description="상점에서 상품을 삭제합니다.")
    @app_commands.describe(상품="삭제할 상품을 선택하세요.")
    @app_commands.autocomplete(상품=item_name_autocomplete)
    async def remove_item(self, interaction: discord.Interaction, 상품: str):
        success = await self.bot.db.shop.remove_item_by_name(상품)
        if success:
            await interaction.response.send_message(f"상품 '{상품}'을(를) 상점에서 삭제했습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("해당 이름의 상품을 찾을 수 없습니다.", ephemeral=True)


async def setup(bot: OverwatchBot):
    await bot.add_cog(ShopCog(bot))

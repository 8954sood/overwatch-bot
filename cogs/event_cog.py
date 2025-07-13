import discord
from discord.ext import commands, tasks
import datetime
import random
import re

from core import OverwatchBot


class EventCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot
        self.voice_sessions = {}  # {user_id: start_time_utc}

    async def cog_load(self):
        if not self.check_expired_roles.is_running():
            print("[TASK] check_expired_roles Started.")
            self.check_expired_roles.start()

    def cog_unload(self):
        print("[TASK] check_expired_roles Stopped.")
        self.check_expired_roles.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if message.guild is None or message.guild.id != self.bot.guild_id:
            return

        await self.bot.db.users.get_or_create_user(message.author.id, message.author.display_name)
        await self.bot.db.users.log_message_activity(message.author.id)

        # Disboard 범프 확인
        if (message.author.id == 302050872383242240 and
                message.interaction and message.interaction.name == "bump"):
            user = message.interaction.user
            await self.bot.db.users.get_or_create_user(user.id, user.display_name)
            await self.bot.db.users.update_balance(user.id, 500)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        if member.bot: return
        user_id = member.id
        await self.bot.db.users.get_or_create_user(user_id, member.display_name)

        if not before.channel and after.channel:
            self.voice_sessions[user_id] = datetime.datetime.now(datetime.timezone.utc)
        elif before.channel and not after.channel:
            if user_id in self.voice_sessions:
                start_time = self.voice_sessions.pop(user_id)
                duration = int((datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds())
                if duration > 0:
                    await self.bot.db.users.log_voice_activity(user_id, duration)

    @tasks.loop(hours=1)
    async def check_expired_roles(self):
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        expired_roles = await self.bot.db.shop.get_expired_roles(now_iso)
        if not expired_roles: return

        guild = self.bot.get_guild(self.bot.guild_id)
        if not guild: return

        removed_ids = []
        for temp_role in expired_roles:
            member = guild.get_member(temp_role.user_id)
            role = guild.get_role(temp_role.role_id)
            if member and role:
                try:
                    await member.remove_roles(role, reason="기간 만료")
                except discord.HTTPException as e:
                    print(f"Failed to remove role {role.id}: {e}")
            removed_ids.append(temp_role.id)

        if removed_ids:
            await self.bot.db.shop.remove_temporary_roles_by_ids(removed_ids)

    @check_expired_roles.before_loop
    async def before_check_roles(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != self.bot.guild_id:
            return

        user = await self.bot.db.users.get_user(member.id)

        if user:
            try:
                await member.edit(nick=user.display_name)
            except discord.Forbidden:
                print(f"Failed to set nickname for {member.display_name} due to permissions.")
            return

        display_name = member.display_name
        if not re.match("^[a-zA-Z가-힣]+$", display_name):
            adjectives = ['행복한', '밝은', '멋진', '빠른', '똑똑한']
            nouns = ['호랑이', '독수리', '사자', '판다', '늑대']
            display_name = f"{random.choice(adjectives)}{random.choice(nouns)}"

        try:
            await member.edit(nick=display_name)
        except discord.Forbidden:
            print(f"Failed to set nickname for {member.display_name} due to permissions.")

        await self.bot.db.users.get_or_create_user(member.id, display_name)


async def setup(bot: OverwatchBot):
    await bot.add_cog(EventCog(bot))

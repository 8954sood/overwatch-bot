import discord
from discord.ext import commands
from core.overwatch_bot import OverwatchBot

class DeveloperCog(commands.Cog):
    def __init__(self, bot: OverwatchBot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @commands.command(name="load")
    @commands.is_owner()
    async def load_cog(self, ctx: commands.Context, cog_name: str):
        try:
            await self.bot.load_extension(f"cogs.{cog_name}")
            await ctx.send(f"Cog '{cog_name}' loaded.")
        except Exception as e:
            await ctx.send(f"Error loading cog '{cog_name}': {e}")

    @commands.command(name="unload")
    @commands.is_owner()
    async def unload_cog(self, ctx: commands.Context, cog_name: str):
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            await ctx.send(f"Cog '{cog_name}' unloaded.")
        except Exception as e:
            await ctx.send(f"Error unloading cog '{cog_name}': {e}")

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx: commands.Context, cog_name: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"Cog '{cog_name}' reloaded.")
        except Exception as e:
            await ctx.send(f"Error reloading cog '{cog_name}': {e}")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_cog(self, ctx: commands.Context):
        guild_obj = discord.Object(id=self.bot.guild_id)
        self.bot.tree.copy_global_to(guild=guild_obj)
        await self.bot.tree.sync(guild=guild_obj)
        await ctx.send(f"Successfully synced {len(self.bot.cogs)} cogs.")

async def setup(bot: OverwatchBot):
    await bot.add_cog(DeveloperCog(bot))

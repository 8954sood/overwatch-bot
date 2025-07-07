from discord.ext import commands

from core import OverwatchBot


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help')
    async def help_command(self, ctx):
        """Displays all available commands."""
        help_text = "Available commands:\n"
        for command in self.bot.commands:
            help_text += f"!{command.name} - {command.help or 'No description'}\n"
        await ctx.send(help_text)

async def setup(bot: OverwatchBot):
    await bot.add_cog(HelpCog(bot))
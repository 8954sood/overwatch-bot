import discord

class RankingView(discord.ui.View):
    def __init__(self, select_callback):
        super().__init__(timeout=30)
        self.select_callback = select_callback
        options = [
            discord.SelectOption(label="재화", value="balance"),
            discord.SelectOption(label="활동량", value="activity"),
        ]
        self.add_item(RankingSelect(options))

class RankingSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="랭킹 종류를 선택하세요.", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.view.select_callback(interaction, self.values[0])


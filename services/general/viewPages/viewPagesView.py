import discord
from discord.ui import View


class ViewPagesView(View):
    
    def __init__(self, previous_func: callable, next_func: callable, timeout: int = 120, buttons: list[discord.ui.Button] = None) -> None:
        super().__init__(timeout=timeout)
        self.previous_func = previous_func
        self.next_func = next_func
        self.buttons = buttons

        if buttons is not None:
            for button in self.buttons:
                self.add_item(button)

    @discord.ui.button(custom_id="previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.previous_func(interaction)

    @discord.ui.button(custom_id="next", style=discord.ButtonStyle.secondary, emoji="➡️")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.next_func(interaction)

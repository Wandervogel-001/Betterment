import discord
from discord.ui import View, Button

from ..ui.attatch_channel_view import AttachChannelView

class ManageSingleEmbedView(View):
    """Panel for managing a single embed's tools."""
    def __init__(self, embed_name: str, embed_service):
        super().__init__(timeout=None)
        self.embed_name = embed_name
        self.embed_service = embed_service

        # Row 0: Management
        self.add_item(AttachChannelButton(embed_service,embed_name))
        self.add_item(SendOptionsButton(embed_name))

        # Row 1: Button Actions
        self.add_item(ManageButtonActionsButton(embed_name))

class AttachChannelButton(Button):
    def __init__(self, embed_service, embed_name):
        super().__init__(label="📌 Attach Channel", style=discord.ButtonStyle.primary)
        self.embed_service = embed_service
        self.embed_name = embed_name

    async def callback(self, interaction: discord.Interaction):
        view = AttachChannelView(self.embed_service, self.embed_name, interaction.guild)
        embed = discord.Embed(
            title=f"Attach Channel to {self.embed_name}",
            description="Select a channel from the dropdown below.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class SendOptionsButton(Button):
    def __init__(self, embed_name: str):
        super().__init__(label="📤 Send Options", style=discord.ButtonStyle.success, row=0)
        self.embed_name = embed_name

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🔧 Send options for `{self.embed_name}` not implemented yet.", ephemeral=True)


class ManageButtonActionsButton(Button):
    def __init__(self, embed_name: str):
        super().__init__(label="🔧 Manage Button Actions", style=discord.ButtonStyle.secondary, row=1)
        self.embed_name = embed_name

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🔧 Button actions for `{self.embed_name}` not implemented yet.", ephemeral=True)


class BackToMainButton(Button):
    def __init__(self):
        super().__init__(label="⬅️ Back", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔧 Returning to main panel not implemented yet.", ephemeral=True)

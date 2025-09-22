import discord
from ..main_panel.panel_modals import CreateEmbedModal
from emojis import PLUS, FOLDER

class BuilderView(discord.ui.View):
    """
    The main, persistent panel for the Embed Builder.
    This view is static and acts as a launchpad for other components.
    """
    def __init__(self, embed_service, embed_sender, panel_manager):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.embed_sender = embed_sender
        self.panel_manager = panel_manager

        # Add the primary action buttons
        self.add_item(BrowseEmbedsButton())
        self.add_item(NewEmbedButton())

class BrowseEmbedsButton(discord.ui.Button):
    """
    Launches a private, ephemeral instance of the Embed Manager panel.
    This allows multiple users to manage embeds concurrently without interference.
    """
    def __init__(self):
        super().__init__(
            label="Browse Embeds",
            emoji=FOLDER,
            style=discord.ButtonStyle.primary,
            custom_id="builder:browse_embeds",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        # The view holds references to the necessary services
        panel_manager = self.view.panel_manager

        # Defer the response as building the panel might take a moment
        await interaction.response.defer(ephemeral=True)

        # Build the embed and view for the manager panel (page 0 by default)
        manager_embed = await panel_manager.build_embed_panel(interaction.guild.id, page=0)
        manager_view = await panel_manager.build_panel_view(interaction.guild.id, page=0)

        # Send the manager panel as an ephemeral message
        await interaction.followup.send(
            embed=manager_embed,
            view=manager_view,
            ephemeral=True
        )

class NewEmbedButton(discord.ui.Button):
    """
    Opens a modal to create a new embed, then launches the editor directly.
    """
    def __init__(self):
        super().__init__(
            label="New Embed",
            emoji=PLUS,
            style=discord.ButtonStyle.success,
            custom_id="builder:new_embed",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        embed_service = self.view.embed_service
        panel_manager = self.view.panel_manager

        # The modal handles creating the embed entry and opening the editor interface
        await interaction.response.send_modal(
            CreateEmbedModal(embed_service, panel_manager)
        )

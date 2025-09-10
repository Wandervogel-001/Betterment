import discord
from discord.ui import View, Button
from ..ui.modals import CreateEmbedModal, EditEmbedModal, DeleteEmbedModal


# ========== Main Panel View ==========
class MainPanelView(View):
    """Persistent Embed Management Panel with primary action buttons."""

    def __init__(self, embed_service, panel_manager):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.panel_manager = panel_manager

        # Row 0: Core CRUD Actions
        self.add_item(CreateNewEmbedButton(self.embed_service, self.panel_manager))
        self.add_item(EditEmbedButton(self.embed_service))
        self.add_item(DeleteEmbedButton(self.embed_service, self.panel_manager))


# ========== Create Button ==========
class CreateNewEmbedButton(Button):
    def __init__(self, embed_service, panel_manager):
        super().__init__(
            label="➕ Create New Embed",
            style=discord.ButtonStyle.green,
            custom_id="embed:create"
        )
        self.embed_service = embed_service
        self.panel_manager = panel_manager

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CreateEmbedModal(self.embed_service, self.panel_manager))


# ========== Edit Button ==========
class EditEmbedButton(Button):
    def __init__(self, embed_service):
        super().__init__(
            label="✏️ Edit Embed",
            style=discord.ButtonStyle.blurple,
            custom_id="embed:edit"
        )
        self.embed_service = embed_service

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditEmbedModal(self.embed_service))


# ========== Delete Button ==========
class DeleteEmbedButton(Button):
    def __init__(self, embed_service, panel_manager):
        super().__init__(
            label="🗑️ Delete Embed",
            style=discord.ButtonStyle.danger,
            custom_id="embed:delete"
        )
        self.embed_service = embed_service
        self.panel_manager = panel_manager

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DeleteEmbedModal(self.embed_service, self.panel_manager))

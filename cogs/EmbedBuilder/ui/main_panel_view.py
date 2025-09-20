import discord
from discord.ui import View, Button
from ..ui.main_panel_modals import CreateEmbedModal, EditEmbedModal, DeleteEmbedModal, RenameEmbedModal, ManageEmbedModal

# ========== Main Panel View ==========
class MainPanelView(View):
    """Persistent Embed Management Panel with primary action buttons."""

    def __init__(self, embed_service, embed_sender, panel_manager):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.embed_sender = embed_sender
        self.panel_manager = panel_manager

        # Row 0: Core CRUD Actions
        self.add_item(CreateNewEmbedButton(self.embed_service, self.panel_manager))
        self.add_item(EditEmbedButton(self.embed_service))
        self.add_item(DeleteEmbedButton(self.embed_service, self.panel_manager))
        # Row 1: Embed Management
        self.add_item(ManageEmbedButton(self.embed_service, self.embed_sender))
        self.add_item(RenameEmbedButton(self.embed_service, self.panel_manager))


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

# ========== Manage Embed Button ==========
class ManageEmbedButton(Button):
    def __init__(self, embed_service, embed_sender):
        super().__init__(
            label="⚙️ Manage Embed",
            style=discord.ButtonStyle.gray,
            custom_id="embed:manage",
            row=1
        )
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ManageEmbedModal(self.embed_service, self.embed_sender))

# ========== Rename Button ==========
class RenameEmbedButton(Button):
    def __init__(self, embed_service, panel_manager):
        super().__init__(
            label="✒️ Rename Embed",
            style=discord.ButtonStyle.secondary,
            custom_id="embed:rename",
            row=1
        )
        self.embed_service = embed_service
        self.panel_manager = panel_manager

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RenameEmbedModal(self.embed_service, self.panel_manager))

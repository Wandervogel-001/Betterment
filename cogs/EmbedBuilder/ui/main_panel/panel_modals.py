import discord
from discord.ui import Modal, TextInput
from ..embed_editor.editor_interface import EmbedEditorView

class CreateEmbedModal(Modal, title="Create New Embed"):
    def __init__(self, embed_service, panel_manager):
        super().__init__()
        self.embed_service = embed_service
        self.panel_manager = panel_manager

    embed_name = TextInput(label="Embed Name", placeholder="e.g. WelcomeEmbed")

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        embed_name = self.embed_name.value.strip()

        if not embed_name:
            await interaction.response.send_message("❌ Embed name cannot be empty.", ephemeral=True)
            return

        empty_config = {
            "title": f"Editing: {embed_name}",
            "description": "Start editing this embed using the buttons below.",
            "color": None, "author": {}, "footer": {},
            "thumbnail": {}, "image": {}, "fields": [], "buttons": []
        }

        await self.embed_service.save_embed_config(guild_id, embed_name, empty_config)

        panel_data = await self.embed_service.get_embed_panel(interaction.guild.id)
        if panel_data:
            await self.panel_manager.refresh_panel_embed(interaction.guild, panel_data["message_id"])

        preview_embed = discord.Embed(
            title=empty_config["title"],
            description=empty_config["description"],
        )
        view = EmbedEditorView(
            embed_service=self.embed_service,
            embed_name=embed_name,
            embed=preview_embed,
            buttons=empty_config['buttons']
        )

        await interaction.response.send_message(embed=preview_embed, view=view, ephemeral=True)

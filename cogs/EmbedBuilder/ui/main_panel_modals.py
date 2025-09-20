import discord
from discord.ui import Modal, TextInput
from ..ui.embed_editor_view import EmbedEditorView
from ..ui.embed_manager_view import ManageSingleEmbedView

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


class EditEmbedModal(Modal, title="Edit Existing Embed"):
    def __init__(self, embed_service):
        super().__init__()
        self.embed_service = embed_service

    embed_name = TextInput(label="Embed Name", placeholder="Enter the name of the embed to edit")

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        embed_name = self.embed_name.value

        config_doc = await self.embed_service.get_embed_config(guild_id, embed_name)
        if config_doc:
            embed_data = config_doc.get('config', {})

            if 'color' in embed_data and embed_data['color'] is None:
                del embed_data['color']

            preview_embed = discord.Embed.from_dict(embed_data)
            buttons = embed_data.get("buttons", [])

            await interaction.response.send_message(
                embed=preview_embed,
                view=EmbedEditorView(
                    embed_service=self.embed_service,
                    embed_name=embed_name,
                    embed=preview_embed,
                    buttons=buttons
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ No embed named `{embed_name}` found.",
                ephemeral=True
            )

class DeleteEmbedModal(Modal, title="Delete Existing Embed"):
    def __init__(self, embed_service, panel_manager):
        super().__init__()
        self.embed_service = embed_service
        self.panel_manager = panel_manager

    embed_name = TextInput(label="Embed Name", placeholder="e.g. WelcomeEmbed")

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        embed_name = self.embed_name.value

        if not await self.embed_service.get_embed_config(guild_id, embed_name):
            await interaction.response.send_message("❌ Embed Not Found!", ephemeral=True)
            return
        await self.embed_service.delete_embed_entry(guild_id, embed_name)
        await interaction.response.send_message("✅ Embed deleted!", ephemeral=True)

        panel_data = await self.embed_service.get_embed_panel(interaction.guild.id)
        if panel_data:
            await self.panel_manager.refresh_panel_embed(interaction.guild, panel_data["message_id"])

class RenameEmbedModal(Modal, title="Rename an Embed"):
    def __init__(self, embed_service, panel_manager):
        super().__init__()
        self.embed_service = embed_service
        self.panel_manager = panel_manager

    current_embed_name = TextInput(
        label="Current Embed Name",
        placeholder="Enter the name of the embed you want to rename",
        required=True
    )

    new_embed_name = TextInput(
        label="New Embed Name",
        placeholder="Enter the new name for the embed",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild.id)
        current_name = self.current_embed_name.value.strip()
        new_name = self.new_embed_name.value.strip()

        if current_name == new_name:
            await interaction.followup.send("⚠️ The new name cannot be the same as the current name.", ephemeral=True)
            return

        # Check if the current embed exists
        config_doc = await self.embed_service.get_embed_config(guild_id, current_name)
        if not config_doc:
            await interaction.followup.send(f"❌ No embed named `{current_name}` found.", ephemeral=True)
            return

        # Check if the new name is already taken
        if await self.embed_service.get_embed_config(guild_id, new_name):
            await interaction.followup.send(f"❌ An embed with the name `{new_name}` already exists.", ephemeral=True)
            return

        embed_config = config_doc.get('config', {})

        # Perform the rename operation
        await self.embed_service.save_embed_config(guild_id, new_name, embed_config)
        await self.embed_service.delete_embed_entry(guild_id, current_name)

        # Refresh the main panel
        panel_data = await self.embed_service.get_embed_panel(interaction.guild.id)
        if panel_data:
            await self.panel_manager.refresh_panel_embed(interaction.guild, panel_data["message_id"])

class ManageEmbedModal(Modal, title="Manage Embed"):
    def __init__(self, embed_service, embed_sender):
        super().__init__()
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    embed_name = TextInput(
        label="Embed Name",
        placeholder="Enter the name of the embed to manage"
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        name = self.embed_name.value

        embeds = await self.embed_service.get_guild_embeds(guild_id)
        if name not in embeds:
            await interaction.response.send_message(
                f"❌ No embed named `{name}` found.",
                ephemeral=True
            )
            return

        preview_embed = discord.Embed(
            title=f"Managing: {name}",
            description="Use the buttons below to configure this embed.",
            color=discord.Color.dark_teal()
        )

        view = ManageSingleEmbedView(name, self.embed_service, self.embed_sender)
        await interaction.response.send_message(embed=preview_embed, view=view, ephemeral=True)

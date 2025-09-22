import discord
from discord.ui import View, Button, Select
from ..embed_editor.editor_interface import EmbedEditorView
from ..embed_editor.sender_modals import WebhookConfigModal
from emojis import (
  NEXT_CHEVRON, PREVIOUS_CHEVRON,
  EDIT, RENAME, TRASH,
  WEBHOOK, SEND
)

# ========== Main Panel View ==========
class EmbedManagerView(View):
    """Redesigned Embed Management Panel with pagination and unified interface."""

    def __init__(self, embed_service, embed_sender, panel_manager, page=0, selected_embed=None, all_embeds=None, attached_channels=None):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.embed_sender = embed_sender
        self.panel_manager = panel_manager
        self.page = page
        self.per_page = 20
        self.selected_embed = selected_embed
        # Ensure all_embeds is never None - if not provided, initialize as empty dict
        self.all_embeds = all_embeds if all_embeds is not None else {}
        # Store attached channels directly as parameter
        self.attached_channels = attached_channels if attached_channels is not None else []

        # Row 0: Navigation and Create
        self._add_navigation_row()

        # Row 1: Embed Selection
        self._add_embed_selection()

        # Row 2: Basic Embed Actions (disabled until embed selected)
        self._add_basic_actions()

        # Row 3: Channel Management (disabled until embed selected)
        self._add_channel_management()

        # Row 4: Advanced Actions (disabled until embed selected)
        self._add_advanced_actions()

    @classmethod
    async def from_db(cls, embed_service, embed_sender, panel_manager, guild_id, page=0, selected_embed=None, attached_channels=None):
        """Factory method to create EmbedManagerView with data loaded from the database."""
        all_embeds = await embed_service.get_guild_embeds(str(guild_id))

        # If attached_channels not provided and an embed is selected, load them
        if attached_channels is None and selected_embed:
            attached_channels = await embed_service.get_attached_channels(str(guild_id), selected_embed)

        instance = cls(
            embed_service=embed_service,
            embed_sender=embed_sender,
            panel_manager=panel_manager,
            page=page,
            selected_embed=selected_embed,
            all_embeds=all_embeds,
            attached_channels=attached_channels
        )

        return instance

    def _add_navigation_row(self):
        """Add navigation buttons and create button to row 0."""
        total_embeds = len(self.all_embeds)

        # Only add navigation if we have more than 20 embeds
        if total_embeds > self.per_page:
            # Previous button
            self.add_item(PrevPageButton(disabled=self.page == 0))

            # Next button
            max_page = (total_embeds - 1) // self.per_page
            self.add_item(NextPageButton(disabled=self.page >= max_page))

    def _add_embed_selection(self):
        """Add embed selection dropdown to row 1."""
        self.add_item(EmbedSelectionDropdown(
            all_embeds=self.all_embeds,
            page=self.page,
            per_page=self.per_page,
            selected_embed=self.selected_embed,
            attached_channels=self.attached_channels
        ))

    def _add_basic_actions(self):
        """Add basic embed action buttons to row 2."""
        has_selection = self.selected_embed is not None

        self.add_item(EditEmbedButton(self.embed_service, disabled=not has_selection))
        self.add_item(RenameEmbedButton(self.embed_service, self.panel_manager, disabled=not has_selection))
        self.add_item(DeleteEmbedButton(self.embed_service, self.panel_manager, disabled=not has_selection))

    def _add_channel_management(self):
        """Add channel attachment management to row 3."""
        has_selection = self.selected_embed is not None

        self.add_item(ChannelAttachmentSelect(
            embed_service=self.embed_service,
            selected_embed=self.selected_embed,
            disabled=not has_selection,
            attached_channels=self.attached_channels
        ))

    def _add_advanced_actions(self):
        """Add advanced action buttons to row 4."""
        has_selection = self.selected_embed is not None

        self.add_item(SendWithBotButton(self.embed_service, self.embed_sender, disabled=not has_selection))
        self.add_item(SendWithWebhookButton(self.embed_service, self.embed_sender, disabled=not has_selection))

# ========== Navigation Buttons (Row 0) ==========
class PrevPageButton(Button):
    def __init__(self, disabled: bool = False):
        super().__init__(
            emoji=PREVIOUS_CHEVRON,
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            custom_id="embed:prev_page",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        new_page = max(0, self.view.page - 1)

        # Build new embed with updated data for the new page
        new_embed = await self.view.panel_manager.build_embed_panel(interaction.guild.id, page=new_page)

        # Build new view with updated page
        new_view = await EmbedManagerView.from_db(
            self.view.embed_service,
            self.view.embed_sender,
            self.view.panel_manager,
            interaction.guild.id,
            page=new_page,
            selected_embed=None,  # Reset selection when changing pages
            attached_channels=[]  # Reset attached channels when changing pages
        )

        await interaction.response.edit_message(embed=new_embed, view=new_view)


class NextPageButton(Button):
    def __init__(self, disabled: bool = False):
        super().__init__(
            emoji=NEXT_CHEVRON,
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            custom_id="embed:next_page",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        new_page = self.view.page + 1

        # Build new embed with updated data for the new page
        new_embed = await self.view.panel_manager.build_embed_panel(interaction.guild.id, page=new_page)

        # Build new view with updated page
        new_view = await EmbedManagerView.from_db(
            self.view.embed_service,
            self.view.embed_sender,
            self.view.panel_manager,
            interaction.guild.id,
            page=new_page,
            selected_embed=None,  # Reset selection when changing pages
            attached_channels=[]  # Reset attached channels when changing pages
        )

        await interaction.response.edit_message(embed=new_embed, view=new_view)


# ========== Embed Selection (Row 1) ==========
class EmbedSelectionDropdown(Select):
    def __init__(self, all_embeds: dict, page: int, per_page: int, selected_embed: str = None, attached_channels: list = None):
        self.all_embeds = all_embeds
        self.page = page
        self.per_page = per_page
        self.attached_channels = attached_channels if attached_channels is not None else []

        # Build options for current page
        options = self._build_options(selected_embed)

        super().__init__(
            placeholder="Select an embed to manage...",
            min_values=0,
            max_values=1,
            options=options,
            custom_id="embed:select_embed",
            row=1
        )

    def _build_options(self, selected_embed: str = None) -> list[discord.SelectOption]:
        """Build select options for the current page."""
        if not self.all_embeds:
            return [discord.SelectOption(
                label="No embeds available",
                value="placeholder",
                description="Create your first embed using the button above"
            )]

        embed_names = list(self.all_embeds.keys())
        start = self.page * self.per_page
        end = start + self.per_page
        paginated_embeds = embed_names[start:end]

        if not paginated_embeds:
            return [discord.SelectOption(
                label="No embeds on this page",
                value="placeholder",
                description="Use navigation buttons to browse other pages"
            )]

        options = []
        for embed_name in paginated_embeds:
            options.append(discord.SelectOption(
                label=embed_name[:100],
                value=embed_name,
                default=(embed_name == selected_embed)
            ))

        return options

    async def callback(self, interaction: discord.Interaction):
        # Handle case where user deselects everything (empty values list)
        if not self.values:
            # User deselected everything - create new view with no selection
            new_view = await EmbedManagerView.from_db(
                self.view.embed_service,
                self.view.embed_sender,
                self.view.panel_manager,
                interaction.guild.id,
                page=self.view.page,
                selected_embed=None,  # No embed selected
                attached_channels=[]  # No attached channels
            )
            await interaction.response.edit_message(view=new_view)
            return

        # Don't process placeholder selections
        if self.values[0] == "placeholder":
            await interaction.response.defer()
            return

        selected_embed = self.values[0]

        # Load attached channels for the selected embed
        attached_channels = await self.view.embed_service.get_attached_channels(
            str(interaction.guild.id), selected_embed
        )

        # Create new view with selected embed and its attached channels
        new_view = await EmbedManagerView.from_db(
            self.view.embed_service,
            self.view.embed_sender,
            self.view.panel_manager,
            interaction.guild.id,
            page=self.view.page,
            selected_embed=selected_embed,
            attached_channels=attached_channels
        )

        await interaction.response.edit_message(view=new_view)


# ========== Basic Actions (Row 2) ==========
class EditEmbedButton(Button):
    def __init__(self, embed_service, disabled: bool = True):
        super().__init__(
            label="Edit",
            emoji=EDIT,
            style=discord.ButtonStyle.primary,
            custom_id="embed:edit",
            disabled=disabled,
            row=2
        )
        self.embed_service = embed_service

    async def callback(self, interaction: discord.Interaction):
        if not self.view.selected_embed:
            await interaction.response.send_message("⚠️ Please select an embed first.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        embed_name = self.view.selected_embed

        config_doc = await self.embed_service.get_embed_config(guild_id, embed_name)
        if not config_doc:
            await interaction.response.send_message(f"❌ Embed `{embed_name}` not found.", ephemeral=True)
            return

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


class RenameEmbedButton(Button):
    def __init__(self, embed_service, panel_manager, disabled: bool = True):
        super().__init__(
            label="Rename",
            emoji=RENAME,
            style=discord.ButtonStyle.secondary,
            custom_id="embed:rename",
            disabled=disabled,
            row=2
        )
        self.embed_service = embed_service
        self.panel_manager = panel_manager

    async def callback(self, interaction: discord.Interaction):
        if not self.view.selected_embed:
            await interaction.response.send_message("⚠️ Please select an embed first.", ephemeral=True)
            return

        # Create a pre-filled rename modal
        modal = PrefilledRenameEmbedModal(
            self.embed_service,
            self.panel_manager,
            current_name=self.view.selected_embed
        )
        await interaction.response.send_modal(modal)


class DeleteEmbedButton(Button):
    def __init__(self, embed_service, panel_manager, disabled: bool = True):
        super().__init__(
            label="Delete",
            emoji=TRASH,
            style=discord.ButtonStyle.danger,
            custom_id="embed:delete",
            disabled=disabled,
            row=2
        )
        self.embed_service = embed_service
        self.panel_manager = panel_manager

    async def callback(self, interaction: discord.Interaction):
        if not self.view.selected_embed:
            await interaction.response.send_message("⚠️ Please select an embed first.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        embed_name = self.view.selected_embed

        # Check if embed exists
        if not await self.embed_service.get_embed_config(guild_id, embed_name):
            await interaction.response.send_message("❌ Embed not found!", ephemeral=True)
            return

        try:
            # Delete the embed
            await self.embed_service.delete_embed_entry(guild_id, embed_name)

            # Build new embed and view to refresh the current ephemeral panel
            new_embed = await self.view.panel_manager.build_embed_panel(interaction.guild.id, page=self.view.page)
            new_view = await EmbedManagerView.from_db(
                self.view.embed_service,
                self.view.embed_sender,
                self.view.panel_manager,
                interaction.guild.id,
                page=self.view.page,
                selected_embed=None,
                attached_channels=[]
            )

            await interaction.response.edit_message(embed=new_embed, view=new_view)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error deleting embed: {str(e)}", ephemeral=True)


# ========== Channel Management (Row 3) ==========
class ChannelAttachmentSelect(discord.ui.ChannelSelect):
    def __init__(self, embed_service, selected_embed: str = None, disabled: bool = True, attached_channels: list = None):
        self.embed_service = embed_service
        self.selected_embed = selected_embed
        self.attached_channels = attached_channels if attached_channels is not None else []

        # Set up default values for already attached channels
        default_values = []
        if not disabled and self.attached_channels:
            default_values = [
                discord.SelectDefaultValue(id=channel_id, type=discord.SelectDefaultValueType.channel)
                for channel_id in self.attached_channels
            ]

        super().__init__(
            placeholder="Select channels to attach to this embed..." if not disabled else f"Select an embed to attach channels to...",
            min_values=0,
            max_values=25,
            channel_types=[discord.ChannelType.text],
            custom_id="embed:attach_channels",
            disabled=disabled,
            row=3,
            default_values=default_values
        )

    async def callback(self, interaction: discord.Interaction):
        if not self.selected_embed:
            await interaction.response.send_message("⚠️ Please select an embed first.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        chosen_channels = [channel.id for channel in self.values]

        # Clear existing attachments and add new ones
        await self.embed_service.clear_channels(guild_id, self.selected_embed)
        for channel_id in chosen_channels:
            await self.embed_service.attach_channel(guild_id, self.selected_embed, channel_id)

        # Create new view with updated attached channels to reflect the changes
        new_view = await EmbedManagerView.from_db(
            self.view.embed_service,
            self.view.embed_sender,
            self.view.panel_manager,
            interaction.guild.id,
            page=self.view.page,
            selected_embed=self.selected_embed,
            attached_channels=chosen_channels
        )

        await interaction.response.edit_message(view=new_view)


# ========== Advanced Actions (Row 4) ==========
class SendWithBotButton(Button):
    def __init__(self, embed_service, embed_sender, disabled: bool = True):
        super().__init__(
            label="Send",
            emoji=SEND,
            style=discord.ButtonStyle.success,
            custom_id="embed:send_bot",
            disabled=disabled,
            row=4
        )
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    async def callback(self, interaction: discord.Interaction):
        if not self.view.selected_embed:
            await interaction.response.send_message("⚠️ Please select an embed first.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        embed_name = self.view.selected_embed

        # Use the attached channels from the view
        attached_channels = self.view.attached_channels

        try:
            results = await self.embed_sender.send_embed(
                interaction=interaction,
                guild_id=guild_id,
                embed_name=embed_name,
                target_channels=attached_channels,
                method="bot"
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)
            return

        # Build summary message
        success = [cid for cid, res in results.items() if res.startswith("sent")]
        failed = [f"<#{cid}> ({res})" for cid, res in results.items() if not res.startswith("sent")]

        if success:
            message = f"✅ Embed `{embed_name}` sent to {len(success)} channel(s)."
            if failed:
                message += f"\n❌ Failed in {len(failed)} channel(s):\n" + "\n".join(failed)
        else:
            message = f"❌ Failed to send embed `{embed_name}` anywhere.\n" + "\n".join(failed)

        await interaction.response.send_message(message, ephemeral=True)


class SendWithWebhookButton(Button):
    def __init__(self, embed_service, embed_sender, disabled: bool = True):
        super().__init__(
            label="Send with Webhook",
            emoji=WEBHOOK,
            style=discord.ButtonStyle.secondary,
            custom_id="embed:send_webhook",
            disabled=disabled,
            row=4
        )
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    async def callback(self, interaction: discord.Interaction):
        if not self.view.selected_embed:
            await interaction.response.send_message("⚠️ Please select an embed first.", ephemeral=True)
            return

        await interaction.response.send_modal(
            WebhookConfigModal(self.view.selected_embed, self.embed_service, self.embed_sender)
        )


# ========== Pre-filled Modals ==========
class PrefilledRenameEmbedModal(discord.ui.Modal, title="Rename Embed"):
    def __init__(self, embed_service, panel_manager, current_name: str):
        super().__init__()
        self.embed_service = embed_service
        self.panel_manager = panel_manager
        self.add_item(discord.ui.TextInput(label="Current Embed Name", default=current_name))
        self.new_embed_name_input = discord.ui.TextInput(label="New Embed Name", placeholder="Enter the new name for the embed")
        self.add_item(self.new_embed_name_input)

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        current_name = self.children[0].value.strip()
        new_name = self.new_embed_name_input.value.strip()

        if not new_name:
            return await interaction.response.send_message("⚠️ The new name cannot be empty.", ephemeral=True)
        if current_name == new_name:
            return await interaction.response.send_message("⚠️ The new name is the same as the current name.", ephemeral=True)
        if await self.embed_service.get_embed_config(guild_id, new_name):
            return await interaction.response.send_message(f"❌ An embed named `{new_name}` already exists.", ephemeral=True)

        # Defer the response since we're doing database operations
        await interaction.response.defer()

        config_doc = await self.embed_service.get_embed_config(guild_id, current_name)
        if config_doc:
            embed_config = config_doc.get('config', {})
            await self.embed_service.save_embed_config(guild_id, new_name, embed_config)
            await self.embed_service.delete_embed_entry(guild_id, current_name)

        try:
            # Get the current page from the original message view
            original_message = interaction.message
            current_page = 0
            if hasattr(original_message, 'components') and original_message.components:
                # Try to extract current page from the view if possible
                # For now, default to page 0 since we don't have easy access to the current page
                pass

            # Build new embed and view to refresh the panel
            new_embed = await self.panel_manager.build_embed_panel(interaction.guild.id, page=current_page)
            new_view = await self.panel_manager.build_panel_view(guild_id=interaction.guild.id, page=current_page)

            # Use edit_original_response since we deferred
            await interaction.edit_original_response(embed=new_embed, view=new_view)

        except (discord.NotFound, discord.Forbidden):
            # If we can't edit the original message, send a follow-up
            await interaction.followup.send(f"✅ Embed renamed from `{current_name}` to `{new_name}`.", ephemeral=True)

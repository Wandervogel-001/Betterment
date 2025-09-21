import discord
from discord.ui import View, Button, Select

from .editor_modals import (
    TitleDescModal, ColorModal, AddFieldModal, EditFieldModal,
    ImageModal, AuthorModal, FooterModal, AddButtonModal, EditButtonModal
)
from ...services.embed_service import EmbedService

from emojis import (
    REMOVE2, PLUS, SAVE2, EDIT2, EDIT, TRASH,
    IMAGES1, COLOR1, FOOTER, TITLE, AUTHOR,
    HAMBURGER_MENU
)

# ========== Embed Editor View ==========
class EmbedEditorView(View):
    """Embed Editor Panel with primary action buttons."""

    def __init__(self, embed_service: EmbedService, embed_name: str, embed: discord.Embed, buttons: list[dict] = None, selected_field_index: int | None = None, selected_button_index: int | None = None):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.selected_field_index: int | None = selected_field_index
        self.selected_button_index: int | None = selected_button_index
        self.buttons = buttons if buttons is not None else []

        # Row 0: Core Properties
        self.add_item(TitleDescButton())
        self.add_item(ColorButton())
        self.add_item(AuthorButton())
        self.add_item(FooterButton())
        self.add_item(ThumbnailImageButton())

        # Row 1: Field Management
        self.add_item(FieldSelect(embed, selected_index=self.selected_field_index))

        # Row 2: Field Actions & save
        self.add_item(AddFieldButton())
        self.add_item(EditFieldButton(disabled=self.selected_field_index is None))
        self.add_item(RemoveFieldButton(disabled=self.selected_field_index is None))
        self.add_item(SaveButton())

        # Row 3: Button Management
        self.add_item(ButtonSelect(self.buttons, selected_index=self.selected_button_index))

        # Row 4: Button Actions
        self.add_item(AddButtonButton())
        self.add_item(EditButton(disabled=self.selected_button_index is None))
        self.add_item(DeleteButton(disabled=self.selected_button_index is None))
        self.add_item(ManageButtonActionsButton(disabled=self.selected_button_index is None))



# ========== Buttons ==========

class TitleDescButton(Button):
    def __init__(self):
        super().__init__(label="Title & Desc", emoji=TITLE, style=discord.ButtonStyle.secondary, custom_id="embed:title_desc", row=0)
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            TitleDescModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, self.view.selected_field_index, self.view.selected_button_index)
        )

class ColorButton(Button):
    def __init__(self):
        super().__init__(label="Color", emoji=COLOR1, style=discord.ButtonStyle.secondary, custom_id="embed:color", row=0)
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            ColorModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, self.view.selected_field_index, self.view.selected_button_index)
        )

class AddFieldButton(Button):
    def __init__(self):
        super().__init__(label="Add Field", emoji=PLUS, style=discord.ButtonStyle.success, custom_id="embed:add_field", row=2)
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            AddFieldModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, self.view.selected_field_index, self.view.selected_button_index)
        )

class EditFieldButton(Button):
    def __init__(self, disabled: bool):
        super().__init__(label="Edit", emoji=EDIT2, style=discord.ButtonStyle.primary, custom_id="embed:edit_field", row=2, disabled=disabled)
    async def callback(self, interaction: discord.Interaction):
        if self.view.selected_field_index is None:
            await interaction.response.send_message("⚠️ Please select a field to edit.", ephemeral=True)
            return
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            EditFieldModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, self.view.selected_field_index, self.view.selected_button_index)
        )

class RemoveFieldButton(Button):
    def __init__(self, disabled: bool):
        super().__init__(
            label="Remove",
            emoji=REMOVE2,
            style=discord.ButtonStyle.danger,
            custom_id="embed:remove_field",
            row=2,
            disabled=disabled
        )
    async def callback(self, interaction: discord.Interaction):
        if self.view.selected_field_index is None:
            await interaction.response.send_message("⚠️ Please select a field to remove.", ephemeral=True)
            return
        embed = interaction.message.embeds[0]
        embed.remove_field(index=self.view.selected_field_index)
        await interaction.response.edit_message(
            embed=embed,
            view=EmbedEditorView(self.view.embed_service, self.view.embed_name, embed, buttons=self.view.buttons, selected_field_index=None, selected_button_index=self.view.selected_button_index)
        )

class ThumbnailImageButton(Button):
    def __init__(self):
        super().__init__(label="Images", emoji=IMAGES1, style=discord.ButtonStyle.secondary, custom_id="embed:thumbnail_image", row=0)
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            ImageModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, self.view.selected_field_index, self.view.selected_button_index)
        )

class AuthorButton(Button):
    def __init__(self):
        super().__init__(label="Author", emoji=AUTHOR, style=discord.ButtonStyle.secondary, custom_id="embed:author", row=0)
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            AuthorModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, self.view.selected_field_index, self.view.selected_button_index)
        )

class FooterButton(Button):
    def __init__(self):
        super().__init__(label="Footer", emoji=FOOTER, style=discord.ButtonStyle.secondary, custom_id="embed:footer", row=0)
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            FooterModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, self.view.selected_field_index, self.view.selected_button_index)
        )

class AddButtonButton(Button):
    def __init__(self):
        super().__init__(label="Add Button", emoji=PLUS, style=discord.ButtonStyle.success, custom_id="embed:add_button", row=4)
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            AddButtonModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, self.view.selected_field_index, self.view.selected_button_index)
        )

class EditButton(Button):
    def __init__(self, disabled: bool):
        super().__init__(label="Edit", emoji=EDIT, style=discord.ButtonStyle.primary, custom_id="embed:edit_button", row=4, disabled=disabled)
    async def callback(self, interaction: discord.Interaction):
        if self.view.selected_button_index is None:
            await interaction.response.send_message("⚠️ Please select a button from the dropdown menu first.", ephemeral=True)
            return
        embed = interaction.message.embeds[0]
        await interaction.response.send_modal(
            EditButtonModal(self.view.embed_service, self.view.embed_name, embed, self.view.buttons, button_index=self.view.selected_button_index, selected_field_index=self.view.selected_field_index)
        )

class DeleteButton(Button):
    def __init__(self, disabled: bool):
        super().__init__(label="Delete", emoji=TRASH, style=discord.ButtonStyle.danger, custom_id="embed:delete_button", row=4, disabled=disabled)
    async def callback(self, interaction: discord.Interaction):
        if self.view.selected_button_index is None:
            await interaction.response.send_message("⚠️ Please select a button to delete.", ephemeral=True)
            return
        embed = interaction.message.embeds[0]
        self.view.buttons.pop(self.view.selected_button_index)
        await interaction.response.edit_message(
            embed=embed,
            view=EmbedEditorView(self.view.embed_service, self.view.embed_name, embed, buttons=self.view.buttons, selected_field_index=self.view.selected_field_index, selected_button_index=None)
        )

class ManageButtonActionsButton(Button):
    def __init__(self, disabled: bool):
        super().__init__(label="Actions", emoji=HAMBURGER_MENU, style=discord.ButtonStyle.secondary, custom_id="embed:manage_button_actions", row=4, disabled=disabled)
    async def callback(self, interaction: discord.Interaction):
        if self.view.selected_button_index is None:
            await interaction.response.send_message("⚠️ Please select a button from the dropdown menu first.", ephemeral=True)
            return

        selected_button_data = self.view.buttons[self.view.selected_button_index]

        # Check if it's a link button (can't have actions)
        if selected_button_data.get("style") == "link":
            await interaction.response.send_message("ℹ️ Link buttons cannot have actions configured.", ephemeral=True)
            return

        # Check if the button has a custom_id
        if not selected_button_data.get("custom_id"):
            await interaction.response.send_message("❌ This button has no custom_id and cannot have actions.", ephemeral=True)
            return

        # Create a factory to return to the current editor view
        def return_to_editor():
            embed = interaction.message.embeds[0]
            return EmbedEditorView(
                self.view.embed_service,
                self.view.embed_name,
                embed,
                buttons=self.view.buttons,
                selected_field_index=self.view.selected_field_index,
                selected_button_index=self.view.selected_button_index
            )

        # Import here to avoid circular imports
        from ..button_actions.action_selector import ButtonSelectionView

        view = ButtonSelectionView(
            embed_name=self.view.embed_name,
            button_data=selected_button_data,
            embed_service=self.view.embed_service,
            previous_view_factory=return_to_editor
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True
        )

class SaveButton(Button):
    def __init__(self):
        super().__init__(label="Save", emoji=SAVE2, style=discord.ButtonStyle.success, custom_id="embed:save", row=2)

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        embed = interaction.message.embeds[0]
        embed_name = self.view.embed_name

        # 1. Construct the new configuration from the editor's current state.
        new_config_data = embed.to_dict()
        if 'color' in new_config_data:
            new_config_data['color'] = embed.color.value
        new_config_data['buttons'] = self.view.buttons

        # 2. Fetch the existing configuration from the database.
        existing_doc = await self.view.embed_service.get_embed_config(guild_id, embed_name)
        existing_config_data = existing_doc.get('config', {}) if existing_doc else {}

        # 3. Compare the two configurations. If they are identical, do nothing.
        if existing_config_data == new_config_data:
            await interaction.response.send_message(
                "⚠️ **No Changes!** There are no new changes to save.",
                ephemeral=True
            )
            return

        # 4. If there are changes, save the new configuration to the database.
        success = await self.view.embed_service.save_embed_config(guild_id, embed_name, new_config_data)

        if success:
            await interaction.response.send_message(f"✅ **Saved!** Your changes to `{embed_name}` have been saved.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ **Error!** Could not save the embed configuration.", ephemeral=True)

# ========== Select Menus ==========
class FieldSelect(Select):
    """A select menu to target a specific embed field for editing or removal."""
    def __init__(self, embed: discord.Embed, selected_index: int | None = None):
        options = []
        if not embed.fields:
            options.append(discord.SelectOption(label="No fields available to select.", value="placeholder", default=True))
        else:
            for i, field in enumerate(embed.fields):
                is_default = (i == selected_index)
                options.append(discord.SelectOption(
                    label=f"Field {i+1}: {field.name[:80]}", value=str(i),
                    description=(field.value[:100] or "No description."), default=is_default
                ))
        super().__init__(placeholder="Select a field to edit or remove...", min_values=1, max_values=1, options=options, row=1, disabled=not embed.fields)

    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        selected_index = int(self.values[0])
        await interaction.response.edit_message(
            view=EmbedEditorView(self.view.embed_service, self.view.embed_name, embed, buttons=self.view.buttons, selected_field_index=selected_index, selected_button_index=self.view.selected_button_index)
        )

class ButtonSelect(Select):
    """A select menu to target a specific button for editing or removal."""
    def __init__(self, buttons: list[dict], selected_index: int | None = None):
        options = []
        if not buttons:
            options.append(discord.SelectOption(label="No buttons available to select.", value="placeholder", default=True))
        else:
            for i, button_data in enumerate(buttons):
                is_default = (i == selected_index)
                label = button_data.get('label', 'No Label')
                desc = button_data.get('custom_id') or button_data.get('url', 'No ID/URL')
                options.append(discord.SelectOption(
                    label=f"Button {i+1}: {label[:80]}", value=str(i),
                    description=desc[:100], default=is_default
                ))
        super().__init__(placeholder="Select a button to edit or remove...", min_values=1, max_values=1, options=options, row=3, disabled=not buttons)

    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        selected_index = int(self.values[0])
        await interaction.response.edit_message(
            view=EmbedEditorView(
                self.view.embed_service, self.view.embed_name, embed, buttons=self.view.buttons,
                selected_field_index=self.view.selected_field_index,
                selected_button_index=selected_index
            )
        )

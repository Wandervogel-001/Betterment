import discord
from discord.ui import View, Select, Button
from .role_picker import RoleSelectionView
from .multi_embed_picker import EmbedSelectionView
from .single_embed_picker import EditEmbedSelectionView
from emojis import ARROW_RIGHT, GO_BACK


class ButtonSelectionView(View):
    def __init__(self, embed_name: str, button_data: dict, embed_service,
                 selected_action_type: str = None, previous_view_factory=None):
        super().__init__(timeout=None)
        self.embed_name = embed_name
        self.embed_service = embed_service
        self.button_data = button_data
        self.selected_action_type = selected_action_type
        self.previous_view_factory = previous_view_factory

        # --- Action Type Select ---
        action_options = [
            discord.SelectOption(label="Add Role", value="add_roles", default=(self.selected_action_type == "add_roles")),
            discord.SelectOption(label="Remove Role", value="remove_roles", default=(self.selected_action_type == "remove_roles")),
            discord.SelectOption(label="Send Embed (as new message)", value="send_embed", default=(self.selected_action_type == "send_embed")),
            discord.SelectOption(label="Edit Embed (replace original message)", value="edit_embed", default=(self.selected_action_type == "edit_embed")),
        ]

        self.action_select = Select(
            placeholder="Choose an action type",
            min_values=1, max_values=1,
            options=action_options
        )
        self.action_select.callback = self._on_action_selected
        self.add_item(self.action_select)

        # --- Next Button ---
        self.next_button = Button(
            label="Next",
            emoji=ARROW_RIGHT,
            style=discord.ButtonStyle.success,
            disabled=(self.selected_action_type is None)
        )
        self.next_button.callback = self._on_next
        self.add_item(self.next_button)

    async def _on_action_selected(self, interaction: discord.Interaction):
        self.selected_action_type = self.action_select.values[0]

        # rebuild the view with updated defaults
        new_view = ButtonSelectionView(
            self.embed_name,
            self.button_data,
            self.embed_service,
            selected_action_type=self.selected_action_type,
            previous_view_factory=self.previous_view_factory
        )
        await interaction.response.edit_message(view=new_view)

    async def _on_next(self, interaction: discord.Interaction):
        if not self.selected_action_type:
            await interaction.response.send_message("❌ Please select an action type.", ephemeral=True)
            return

        action = self.selected_action_type
        custom_id = self.button_data.get("custom_id")

        if not custom_id:
            await interaction.response.send_message("❌ This button has no custom_id and cannot have actions.", ephemeral=True)
            return

        # --- Create the previous_view factory ---
        previous_factory = lambda: ButtonSelectionView(
            self.embed_name,
            self.button_data,
            self.embed_service,
            selected_action_type=action,
            previous_view_factory=self.previous_view_factory
        )

        if action in ("add_roles", "remove_roles"):
            view = await RoleSelectionView.from_db(
                self.embed_service,
                interaction.guild,
                self.embed_name,
                custom_id,
                action,
                previous_view_factory=previous_factory
            )
            await interaction.response.edit_message(view=view)

        elif action == "send_embed":
            view = await EmbedSelectionView.from_db(
                self.embed_service,
                interaction.guild,
                self.embed_name,
                custom_id,
                previous_view_factory=previous_factory
            )
            await interaction.response.edit_message(view=view)

        elif action == "edit_embed":
            view = await EditEmbedSelectionView.from_db(
                self.embed_service,
                interaction.guild,
                self.embed_name,
                custom_id,
                previous_view_factory=previous_factory
            )
            await interaction.response.edit_message(view=view)

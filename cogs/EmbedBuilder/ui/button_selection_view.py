import discord
from discord.ui import View, Select, Button
from ..ui.role_selection_view import RoleSelectionView
from ..ui.embed_selection_view import EmbedSelectionView
from ..ui.edit_embed_selection_view import EditEmbedSelectionView
from emojis import ARROW_RIGHT


class ButtonSelectionView(View):
    def __init__(self, embed_name: str, buttons: list[dict], embed_service,
                 selected_custom_id: str = None, selected_action_type: str = None):
        super().__init__(timeout=None)
        self.embed_name = embed_name
        self.embed_service = embed_service
        self.buttons = buttons
        self.selected_custom_id = selected_custom_id
        self.selected_action_type = selected_action_type

        # --- Button Select ---
        button_options = []
        for i, btn in enumerate(self.buttons):
            if btn.get("style") == "link":
                continue  # skip link buttons
            cid = btn.get("custom_id", f"placeholder_{i}")
            button_options.append(discord.SelectOption(
                label=btn.get("label", "No Label"),
                description=cid,
                value=cid,
                default=(cid == self.selected_custom_id)
            ))

        self.button_select = Select(
            placeholder="Select a button",
            min_values=1, max_values=1,
            options=button_options
        )
        self.button_select.callback = self._on_button_selected
        self.add_item(self.button_select)

        # --- Action Type Select ---
        action_options = [
            discord.SelectOption(label="Add Role", value="add_roles", default=(self.selected_action_type == "add_roles")),
            discord.SelectOption(label="Remove Role", value="remove_roles", default=(self.selected_action_type == "remove_roles")),
            discord.SelectOption(label="Send Embed (as new message)", value="send_embed", default=(self.selected_action_type == "send_embed")),
            # Add the new option here
            discord.SelectOption(label="Edit Embed (replace original message)", value="edit_embed", default=(self.selected_action_type == "edit_embed")),
        ]

        self.action_select = Select(
            placeholder="Choose an action type",
            min_values=1, max_values=1,
            options=action_options,
            disabled=(self.selected_custom_id is None)
        )
        self.action_select.callback = self._on_action_selected
        self.add_item(self.action_select)


        # --- Next Button ---
        self.next_button = Button(
            label="Next",
            emoji=ARROW_RIGHT,
            style=discord.ButtonStyle.success,
            disabled=not (self.selected_custom_id and self.selected_action_type)
        )
        self.next_button.callback = self._on_next
        self.add_item(self.next_button)

    async def _on_button_selected(self, interaction: discord.Interaction):
        self.selected_custom_id = self.button_select.values[0]

        # rebuild the view with updated defaults
        new_view = ButtonSelectionView(
            self.embed_name,
            self.buttons,
            self.embed_service,
            selected_custom_id=self.selected_custom_id,
            selected_action_type=self.selected_action_type
        )
        await interaction.response.edit_message(view=new_view)

    async def _on_action_selected(self, interaction: discord.Interaction):
        self.selected_action_type = self.action_select.values[0]

        # rebuild the view with updated defaults
        new_view = ButtonSelectionView(
            self.embed_name,
            self.buttons,
            self.embed_service,
            selected_custom_id=self.selected_custom_id,
            selected_action_type=self.selected_action_type
        )
        await interaction.response.edit_message(view=new_view)

    async def _on_next(self, interaction: discord.Interaction):
        if not (self.selected_custom_id and self.selected_action_type):
            await interaction.response.send_message("❌ Please select both a button and an action.", ephemeral=True)
            return

        action = self.selected_action_type
        custom_id = self.selected_custom_id

        # --- Create the previous_view factory (used by all action types) ---
        previous_factory = lambda: ButtonSelectionView(
            self.embed_name,
            self.buttons,
            self.embed_service,
            selected_custom_id=custom_id,
            selected_action_type=action
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

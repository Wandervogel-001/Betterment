import discord
from discord.ui import View, Select, Button
from typing import List, Dict, Any
from emojis import CHECKMARK, GO_BACK, NEXT_CHEVRON, PREVIOUS_CHEVRON

class EditEmbedSelectionView(View):
    def __init__(self, embed_service, guild, embed_name, custom_id,
                 selected_embed=None, previous_view_factory=None, page=0, all_embeds=None):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.guild = guild
        self.embed_name = embed_name # The original embed's name
        self.custom_id = custom_id # The button's custom_id
        self.selected_embed = selected_embed
        self.previous_view_factory = previous_view_factory
        self.page = page
        self.per_page = 25
        self.all_embeds = all_embeds or {}

        # Initialize view components
        self.add_item(EmbedSingleSelect(
            selected_embed=self.selected_embed,
            page=self.page,
            per_page=self.per_page,
            all_embeds=self.all_embeds
        ))

        # Pagination buttons
        if len(self.all_embeds) > self.per_page:
            self.add_item(PrevPageButton(disabled=self.page == 0))
            is_last_page = (self.page + 1) * self.per_page >= len(self.all_embeds)
            self.add_item(NextPageButton(disabled=is_last_page))

        # Action buttons
        self.add_item(BackButton(self.previous_view_factory))
        self.add_item(SubmitButton())

    @classmethod
    async def from_db(cls, embed_service, guild, embed_name, custom_id, previous_view_factory=None):
        """Factory method to create EditEmbedSelectionView with data loaded from the database."""
        existing_embed = await cls._get_existing_embed_from_db(
            embed_service, str(guild.id), embed_name, custom_id
        )
        all_embeds = await embed_service.get_guild_embeds(str(guild.id))

        return cls(
            embed_service=embed_service,
            guild=guild,
            embed_name=embed_name,
            custom_id=custom_id,
            selected_embed=existing_embed,
            previous_view_factory=previous_view_factory,
            all_embeds=all_embeds
        )

    @staticmethod
    async def _get_existing_embed_from_db(embed_service, guild_id, embed_name, custom_id):
        """Get the existing embed name for the edit_embed action from the database."""
        actions = await embed_service.list_button_actions(guild_id, embed_name, custom_id)
        for action in actions:
            if action.get("type") == "edit_embed":
                return action.get("embed_name")
        return None


class EmbedSingleSelect(Select):
    def __init__(self, selected_embed: str, page: int, per_page: int, all_embeds: Dict[str, Any]):
        # Build options for the current page
        embed_names = list(all_embeds.keys())
        start = page * per_page
        end = start + per_page
        paginated_embeds = embed_names[start:end]

        options = []
        if not paginated_embeds:
            options.append(discord.SelectOption(label="No embeds on this page", value="placeholder"))
        else:
            for name in paginated_embeds:
                options.append(discord.SelectOption(
                    label=name[:100],
                    value=name,
                    default=(name == selected_embed)
                ))

        super().__init__(
            placeholder="Select one embed to replace the message with",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="embed:select_single_embed"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "placeholder":
            await interaction.response.defer()
            return

        view = self.view
        # Recreate the view with the new selection
        new_view = EditEmbedSelectionView(
            embed_service=view.embed_service,
            guild=view.guild,
            embed_name=view.embed_name,
            custom_id=view.custom_id,
            selected_embed=self.values[0],
            previous_view_factory=view.previous_view_factory,
            page=view.page,
            all_embeds=view.all_embeds
        )
        await interaction.response.edit_message(view=new_view)


class PrevPageButton(Button):
    def __init__(self, disabled: bool = False):
        super().__init__(emoji=PREVIOUS_CHEVRON, style=discord.ButtonStyle.secondary, disabled=disabled, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        new_page = max(0, view.page - 1)
        new_view = EditEmbedSelectionView(
            embed_service=view.embed_service, guild=view.guild, embed_name=view.embed_name,
            custom_id=view.custom_id, selected_embed=view.selected_embed,
            previous_view_factory=view.previous_view_factory, page=new_page, all_embeds=view.all_embeds
        )
        await interaction.response.edit_message(view=new_view)


class NextPageButton(Button):
    def __init__(self, disabled: bool = False):
        super().__init__(emoji=NEXT_CHEVRON, style=discord.ButtonStyle.secondary, disabled=disabled, row=1)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        new_page = view.page + 1
        new_view = EditEmbedSelectionView(
            embed_service=view.embed_service, guild=view.guild, embed_name=view.embed_name,
            custom_id=view.custom_id, selected_embed=view.selected_embed,
            previous_view_factory=view.previous_view_factory, page=new_page, all_embeds=view.all_embeds
        )
        await interaction.response.edit_message(view=new_view)


class BackButton(Button):
    def __init__(self, previous_view_factory):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, emoji=GO_BACK, row=2)
        self.previous_view_factory = previous_view_factory

    async def callback(self, interaction: discord.Interaction):
        if self.previous_view_factory:
            await interaction.response.edit_message(view=self.previous_view_factory())
        else:
            await interaction.response.send_message("❌ Cannot go back.", ephemeral=True)


class SubmitButton(Button):
    def __init__(self):
        super().__init__(label="Submit", emoji=CHECKMARK, style=discord.ButtonStyle.success, row=2)

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        selected_embed = self.view.selected_embed

        if not selected_embed:
            await interaction.response.send_message("⚠️ No embed selected. Please choose one to continue.", ephemeral=True)
            return

        try:
            await self._update_button_embed_edit(guild_id, selected_embed)
            response = (
                f"✅ Button `{self.view.custom_id}` will now **edit the message** "
                f"and display the `{selected_embed}` embed when clicked."
            )
            await interaction.response.send_message(response, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ **Error saving configuration:** {str(e)}", ephemeral=True)

    async def _update_button_embed_edit(self, guild_id: str, embed_name: str):
        """Update or create the edit_embed action in the database."""
        view = self.view
        existing_actions = await view.embed_service.list_button_actions(guild_id, view.embed_name, view.custom_id)

        # Remove any old edit_embed actions
        filtered_actions = [action for action in existing_actions if action.get("type") != "edit_embed"]

        # Add the new action
        new_action = {"type": "edit_embed", "embed_name": embed_name}
        filtered_actions.append(new_action)

        # Update the database
        await view.embed_service.update_button_actions(guild_id, view.embed_name, view.custom_id, filtered_actions)

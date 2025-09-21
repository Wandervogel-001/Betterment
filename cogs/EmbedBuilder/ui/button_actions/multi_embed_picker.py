import discord
from discord.ui import View, Select, Button
from typing import List, Dict, Any, Tuple
from emojis import CHECKMARK, GO_BACK, NEXT_CHEVRON, PREVIOUS_CHEVRON

class EmbedSelectionView(View):
    def __init__(self, embed_service, guild, embed_name, custom_id,
                 selected_embeds=None, previous_view_factory=None, page=0, compatible_embeds=None):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.guild = guild
        self.embed_name = embed_name
        self.custom_id = custom_id
        self.selected_embeds = selected_embeds or []
        self.previous_view_factory = previous_view_factory
        self.page = page
        self.per_page = 25

        # Cache for embed character counts
        self.embed_char_counts = {}
        self.available_embeds = {}
        self.compatible_embeds = compatible_embeds or {}

        # Initialize view components
        self.add_item(EmbedMultiSelect(
            embed_service=embed_service,
            guild_id=str(guild.id),
            selected_embeds=self.selected_embeds,
            page=self.page,
            per_page=self.per_page,
            parent_view=self,
            compatible_embeds=self.compatible_embeds
        ))

        # Navigation buttons (pagination)
        total_embeds = len(self.compatible_embeds)
        if total_embeds > self.per_page:
            self.add_item(PrevPageButton(disabled=self.page == 0))
            self.add_item(NextPageButton()) # Will be enabled/disabled dynamically

        # Action buttons
        self.add_item(BackButton(self.previous_view_factory))
        self.add_item(SubmitButton())

    @classmethod
    async def from_db(cls, embed_service, guild, embed_name, custom_id, previous_view_factory=None):
        """Factory method to create EmbedSelectionView with embeds loaded from database."""
        existing_embeds = await cls._get_existing_embeds_from_db(
            embed_service, str(guild.id), embed_name, custom_id
        )

        # Pre-calculate compatible embeds
        instance = cls.__new__(cls)  # Create instance without calling __init__
        instance.embed_service = embed_service
        instance.guild = guild
        instance.embed_name = embed_name
        instance.custom_id = custom_id
        instance.selected_embeds = existing_embeds
        instance.previous_view_factory = previous_view_factory
        instance.page = 0
        instance.per_page = 25
        instance.embed_char_counts = {}
        instance.available_embeds = {}

        # Calculate compatible embeds before initializing view
        compatible_embeds, _ = await instance.get_compatible_embeds(str(guild.id), existing_embeds)

        # Now properly initialize the view
        return cls(
            embed_service=embed_service,
            guild=guild,
            embed_name=embed_name,
            custom_id=custom_id,
            selected_embeds=existing_embeds,
            previous_view_factory=previous_view_factory,
            compatible_embeds=compatible_embeds
        )

    @staticmethod
    async def _get_existing_embeds_from_db(embed_service, guild_id, embed_name, custom_id):
        """Get existing embed names for the send_embed action from the database."""
        actions = await embed_service.list_button_actions(guild_id, embed_name, custom_id)

        for action in actions:
            if action.get("type") == "send_embed":
                return action.get("embed_names", [])

        return []

    async def update_view_with_new_selection(self, interaction, new_selected_embeds):
        """Update the view when embed selection changes."""
        self.selected_embeds = new_selected_embeds

        # Recalculate compatible embeds
        compatible_embeds, _ = await self.get_compatible_embeds(str(self.guild.id), self.selected_embeds)

        # Create new view with updated selection
        new_view = EmbedSelectionView(
            embed_service=self.embed_service,
            guild=self.guild,
            embed_name=self.embed_name,
            custom_id=self.custom_id,
            selected_embeds=self.selected_embeds,
            previous_view_factory=self.previous_view_factory,
            page=self.page,
            compatible_embeds=compatible_embeds
        )

        await interaction.response.edit_message(view=new_view)

    def calculate_embed_character_count(self, embed_config: Dict[str, Any]) -> int:
        """Calculate the character count for an embed configuration."""
        char_count = 0

        # Title
        if embed_config.get("title"):
            char_count += len(embed_config["title"])

        # Description
        if embed_config.get("description"):
            char_count += len(embed_config["description"])

        # Author name
        author = embed_config.get("author", {})
        if author.get("name"):
            char_count += len(author["name"])

        # Footer text
        footer = embed_config.get("footer", {})
        if footer.get("text"):
            char_count += len(footer["text"])

        # Fields
        fields = embed_config.get("fields", [])
        for field in fields:
            if field.get("name"):
                char_count += len(field["name"])
            if field.get("value"):
                char_count += len(field["value"])

        return char_count

    async def get_compatible_embeds(self, guild_id: str, selected_embeds: List[str]) -> Tuple[Dict[str, int], int]:
        """
        Get embeds that can fit within Discord's 6000 character limit.
        Returns: (compatible_embeds_dict, remaining_characters)
        """
        all_embeds = await self.embed_service.get_guild_embeds(guild_id)

        # Calculate total characters used by selected embeds
        used_characters = 0
        selected_char_counts = {}

        for embed_name in selected_embeds:
            if embed_name in all_embeds:
                embed_config = all_embeds[embed_name].get("config", {})
                char_count = self.calculate_embed_character_count(embed_config)
                selected_char_counts[embed_name] = char_count
                used_characters += char_count

        remaining_characters = 6000 - used_characters

        # Find compatible embeds (those that fit in remaining space)
        compatible_embeds = {}

        for embed_name, embed_data in all_embeds.items():
            if embed_name in selected_embeds:
                # Already selected embeds are always "compatible"
                compatible_embeds[embed_name] = selected_char_counts[embed_name]
            else:
                embed_config = embed_data.get("config", {})
                char_count = self.calculate_embed_character_count(embed_config)

                # Check if this embed can fit in remaining space
                if char_count <= remaining_characters:
                    compatible_embeds[embed_name] = char_count

        return compatible_embeds, remaining_characters


class EmbedMultiSelect(Select):
    def __init__(self, embed_service, guild_id: str, selected_embeds: List[str],
                 page: int, per_page: int, parent_view, compatible_embeds: Dict[str, int]):
        self.embed_service = embed_service
        self.guild_id = guild_id
        self.selected_embeds = selected_embeds
        self.page = page
        self.per_page = per_page
        self.parent_view = parent_view
        self.compatible_embeds = compatible_embeds

        # Initialize options immediately
        options = self._build_options()

        super().__init__(
            placeholder="Select embeds to send",
            min_values=0,
            max_values=min(10, len(options)) if options else 1,  # Discord's maximum embeds per message
            options=options,
            custom_id="embed:select_embeds"
        )

    def _build_options(self) -> List[discord.SelectOption]:
        """Build select options based on compatible embeds and pagination."""
        if not self.compatible_embeds:
            return [discord.SelectOption(
                label="No compatible embeds available",
                value="placeholder",
                description="Character limit reached or no embeds exist"
            )]

        # Calculate remaining characters
        used_characters = sum(self.compatible_embeds[name] for name in self.selected_embeds
                            if name in self.compatible_embeds)
        remaining_chars = 6000 - used_characters

        # Get paginated slice of compatible embeds
        embed_names = list(self.compatible_embeds.keys())
        start = self.page * self.per_page
        end = start + self.per_page
        paginated_embeds = embed_names[start:end]

        if not paginated_embeds:
            return [discord.SelectOption(
                label="No embeds on this page",
                value="placeholder",
                description="Use navigation buttons to browse"
            )]

        options = []
        for embed_name in paginated_embeds:
            char_count = self.compatible_embeds[embed_name]
            is_selected = embed_name in self.selected_embeds

            # Create description with character info
            if is_selected:
                description = f"Selected • {char_count} chars"
            else:
                description = f"{char_count} chars • {remaining_chars} remaining"

            options.append(discord.SelectOption(
                label=embed_name[:100],  # Discord label limit
                value=embed_name,
                description=description[:100],  # Discord description limit
                default=is_selected
            ))

        return options

    async def callback(self, interaction: discord.Interaction):
        # Don't process placeholder selections
        if self.values and self.values[0] == "placeholder":
            await interaction.response.defer()
            return

        # Get newly selected embed names
        new_selected_embeds = self.values.copy()

        # Validate selection against character limits
        compatible_embeds, remaining_chars = await self.parent_view.get_compatible_embeds(
            self.guild_id, new_selected_embeds
        )

        # Filter out incompatible selections
        valid_selections = [name for name in new_selected_embeds if name in compatible_embeds]

        # Update parent view with valid selections
        await self.parent_view.update_view_with_new_selection(interaction, valid_selections)


class PrevPageButton(Button):
    def __init__(self, disabled: bool = False):
        super().__init__(
            emoji=PREVIOUS_CHEVRON,
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        new_page = max(0, self.view.page - 1)

        # Recalculate compatible embeds
        compatible_embeds, _ = await self.view.get_compatible_embeds(
            str(self.view.guild.id), self.view.selected_embeds
        )

        new_view = EmbedSelectionView(
            embed_service=self.view.embed_service,
            guild=self.view.guild,
            embed_name=self.view.embed_name,
            custom_id=self.view.custom_id,
            selected_embeds=self.view.selected_embeds,
            previous_view_factory=self.view.previous_view_factory,
            page=new_page,
            compatible_embeds=compatible_embeds
        )

        await interaction.response.edit_message(view=new_view)


class NextPageButton(Button):
    def __init__(self, disabled: bool = False):
        super().__init__(
            emoji=NEXT_CHEVRON,
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        # Check if there are more pages
        compatible_embeds, _ = await self.view.get_compatible_embeds(
            str(self.view.guild.id), self.view.selected_embeds
        )

        total_embeds = len(compatible_embeds)
        max_page = (total_embeds - 1) // self.view.per_page

        if self.view.page >= max_page:
            await interaction.response.defer()
            return

        new_view = EmbedSelectionView(
            embed_service=self.view.embed_service,
            guild=self.view.guild,
            embed_name=self.view.embed_name,
            custom_id=self.view.custom_id,
            selected_embeds=self.view.selected_embeds,
            previous_view_factory=self.view.previous_view_factory,
            page=self.view.page + 1,
            compatible_embeds=compatible_embeds
        )

        await interaction.response.edit_message(view=new_view)


class BackButton(Button):
    def __init__(self, previous_view_factory):
        super().__init__(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji=GO_BACK,
            row=2
        )
        self.previous_view_factory = previous_view_factory

    async def callback(self, interaction: discord.Interaction):
        if self.previous_view_factory:
            previous_view = self.previous_view_factory()
            await interaction.response.edit_message(view=previous_view)
        else:
            await interaction.response.send_message("❌ Cannot go back - no previous view available.", ephemeral=True)


class SubmitButton(Button):
    def __init__(self):
        super().__init__(
            label="Submit",
            emoji=CHECKMARK,
            style=discord.ButtonStyle.success,
            row=2
        )

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        selected_embeds = self.view.selected_embeds

        if not selected_embeds:
            await interaction.response.send_message(
                "⚠️ No embeds selected. The send_embed action will be removed.",
                ephemeral=True
            )

        try:
            # Update the database with the embed configuration
            await self._update_button_embeds(guild_id, selected_embeds)

            # Build response message
            if selected_embeds:
                # Calculate final character usage for confirmation
                compatible_embeds, _ = await self.view.get_compatible_embeds(guild_id, selected_embeds)
                total_chars = sum(compatible_embeds.get(name, 0) for name in selected_embeds)

                embed_list = ", ".join(f"`{name}`" for name in selected_embeds)
                response = (
                    f"✅ **{len(selected_embeds)} embeds** configured for button `{self.view.custom_id}`:\n"
                    f"{embed_list}\n\n"
                    f"📊 **Total character usage:** {total_chars}/6,000 ({6000-total_chars} remaining)"
                )
            else:
                response = f"ℹ️ **Send embed action removed** from button `{self.view.custom_id}`."

            await interaction.response.send_message(response, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ **Error saving embed configuration:** {str(e)}", ephemeral=True)

    async def _update_button_embeds(self, guild_id: str, embed_names: List[str]):
        """Update or create the send_embed action in the database, ensuring no duplicates."""
        # Get all existing actions for this button
        existing_actions = await self.view.embed_service.list_button_actions(
            guild_id, self.view.embed_name, self.view.custom_id
        )

        # Filter out any existing send_embed actions
        filtered_actions = [
            action for action in existing_actions
            if action.get("type") != "send_embed"
        ]

        # Add the new send_embed action if there are embeds to configure
        if embed_names:
            new_action = {
                "type": "send_embed",
                "embed_names": embed_names,
                "ephemeral": True  # Default to ephemeral for embed responses
            }
            filtered_actions.append(new_action)

        # Update the database with the filtered actions
        await self.view.embed_service.update_button_actions(
            guild_id, self.view.embed_name, self.view.custom_id, filtered_actions
        )

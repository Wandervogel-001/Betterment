import discord
from discord.ui import View, RoleSelect, Button
from emojis import GO_BACK, CHECKMARK

class RoleSelectionView(View):
    def __init__(self, embed_service, guild, embed_name, custom_id, action_type,
                 selected_roles=None, previous_view_factory=None):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.guild = guild
        self.embed_name = embed_name
        self.custom_id = custom_id
        self.action_type = action_type
        self.selected_roles = selected_roles or []
        self.previous_view_factory = previous_view_factory

        # Add the role select component
        self.add_item(RoleMultiSelect(self.selected_roles))

        # Add back button
        self.add_item(BackButton(self.previous_view_factory))

        # Add submit button
        self.add_item(SubmitButton())

    @classmethod
    async def from_db(cls, embed_service, guild, embed_name, custom_id, action_type, previous_view_factory=None):
        """Factory method to create RoleSelectionView with roles loaded from database."""
        # Get existing roles for this button action from database
        existing_roles = await cls._get_existing_roles_from_db(
            embed_service, str(guild.id), embed_name, custom_id, action_type
        )

        return cls(
            embed_service=embed_service,
            guild=guild,
            embed_name=embed_name,
            custom_id=custom_id,
            action_type=action_type,
            selected_roles=existing_roles,
            previous_view_factory=previous_view_factory
        )

    @staticmethod
    async def _get_existing_roles_from_db(embed_service, guild_id, embed_name, custom_id, action_type):
        """Get existing role IDs for the given action type from the database."""
        actions = await embed_service.list_button_actions(guild_id, embed_name, custom_id)

        for action in actions:
            if action.get("type") == action_type:
                return action.get("role_ids", [])

        return []


class RoleMultiSelect(RoleSelect):
    def __init__(self, selected_role_ids):
        # Convert role IDs to SelectDefaultValue objects for default selection
        default_values = [
            discord.SelectDefaultValue(id=role_id, type=discord.SelectDefaultValueType.role)
            for role_id in selected_role_ids
        ]

        super().__init__(
            placeholder="Select roles for this action...",
            min_values=0,
            max_values=25,  # Discord's maximum for select menus
            default_values=default_values,
            custom_id="role:select_roles"
        )

    async def callback(self, interaction: discord.Interaction):
        # Silently acknowledge the interaction without doing anything
        # The submit button will handle the database operations
        await interaction.response.defer()


class BackButton(Button):
    def __init__(self, previous_view_factory):
        super().__init__(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji=GO_BACK
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
            style=discord.ButtonStyle.success,
            emoji=CHECKMARK
        )

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        # Get selected roles from the RoleSelect component
        role_select = None
        for item in self.view.children:
            if isinstance(item, RoleMultiSelect):
                role_select = item
                break

        if not role_select:
            await interaction.response.send_message("❌ Role selection component not found.", ephemeral=True)
            return

        selected_role_ids = [role.id for role in role_select.values]

        # Validate roles and filter out invalid ones
        valid_role_ids = await self._validate_roles(interaction.guild, selected_role_ids)

        # Check for conflicts with opposite action type
        conflicting_roles = await self._check_role_conflicts(
            guild_id, valid_role_ids, self.view.action_type
        )

        # Remove conflicting roles from valid selection
        final_role_ids = [rid for rid in valid_role_ids if rid not in conflicting_roles]

        try:
            # Update the database with the new role configuration
            await self._update_button_roles(guild_id, final_role_ids)

            # Build response message
            response_parts = []

            if final_role_ids:
                role_mentions = [f"<@&{rid}>" for rid in final_role_ids]
                action_name = "added to" if self.view.action_type == "add_roles" else "removed from"
                response_parts.append(
                    f"✅ **{len(final_role_ids)} roles** will be **{action_name}** users when they click `{self.view.custom_id}`:\n"
                    f"{', '.join(role_mentions)}"
                )
            else:
                action_name = "addition" if self.view.action_type == "add_roles" else "removal"
                response_parts.append(f"ℹ️ No roles configured for **{action_name}** on button `{self.view.custom_id}`.")

            if conflicting_roles:
                opposite_action = "remove_roles" if self.view.action_type == "add_roles" else "add_roles"
                conflicting_mentions = [f"<@&{rid}>" for rid in conflicting_roles]
                response_parts.append(
                    f"\n⚠️ **{len(conflicting_roles)} roles** were ignored due to conflicts with **{opposite_action}**:\n"
                    f"{', '.join(conflicting_mentions)}"
                )

            invalid_count = len(selected_role_ids) - len(valid_role_ids)
            if invalid_count > 0:
                response_parts.append(f"\n⚠️ **{invalid_count} roles** were ignored (deleted or inaccessible).")

            await interaction.response.send_message("\n".join(response_parts), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ **Error saving role configuration:** {str(e)}", ephemeral=True)

    async def _validate_roles(self, guild, role_ids):
        """Validate that roles exist and are accessible."""
        valid_roles = []
        for role_id in role_ids:
            role = guild.get_role(role_id)
            if role:
                valid_roles.append(role_id)
        return valid_roles

    async def _check_role_conflicts(self, guild_id, role_ids, current_action_type):
        """Check for roles that exist in the opposite action type."""
        opposite_action = "remove_roles" if current_action_type == "add_roles" else "add_roles"

        # Get existing roles for the opposite action
        existing_opposite_roles = await RoleSelectionView._get_existing_roles_from_db(
            self.view.embed_service, guild_id, self.view.embed_name,
            self.view.custom_id, opposite_action
        )

        # Find conflicts
        return [rid for rid in role_ids if rid in existing_opposite_roles]

    async def _update_button_roles(self, guild_id, role_ids):
        """Update or create the role action in the database, ensuring no duplicates."""
        # Get all existing actions for this button
        existing_actions = await self.view.embed_service.list_button_actions(
            guild_id, self.view.embed_name, self.view.custom_id
        )

        # Filter out any existing actions of the same type
        filtered_actions = [
            action for action in existing_actions
            if action.get("type") != self.view.action_type
        ]

        # Add the new action if there are roles to configure
        if role_ids:
            new_action = {
                "type": self.view.action_type,
                "role_ids": role_ids
            }
            filtered_actions.append(new_action)

        # Update the database with the filtered actions
        await self.view.embed_service.update_button_actions(
            guild_id, self.view.embed_name, self.view.custom_id, filtered_actions
        )

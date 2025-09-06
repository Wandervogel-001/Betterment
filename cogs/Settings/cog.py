import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging
from typing import List, Dict, Any
from ..TeamsPanel.permissions import moderator_required

from .services.settings_service import SettingsService
from .ui.ai_model_selection import AIModelSelectionView

logger = logging.getLogger(__name__)

# Configuration for available settings. This is the single source of truth for what can be configured.
# To add a new setting, you just need to add it here.
SETTING_TYPES: Dict[str, Dict[str, Any]] = {
    "category": {
        "name": "Categories",
        "fields": {
            "marathon_category": "The category where new marathon team channels will be created."
        }
    },
    "channel": {
        "name": "Channels",
        "fields": {
            "marathon_registration_channel": "The channel for marathon registration embed.",
            "communication_channel": "The channel for communication messages.",
            "news_channel": "The channel for news and challenges messages.",
            "heroes_channel": "The channel for heroes posts and messages.",
            "only_leaders_channel": "The channel for only leaders embed.",
            "leaders_chat": "The channel for leaders chat messages.",
        }
    }
}

class SettingsCog(commands.Cog):
    """
    A cog for managing extensible, server-specific settings for the bot.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
        self.SETTING_TYPES = SETTING_TYPES
        self.settings_service = SettingsService(self.db)

    # ========== AUTOCOMPLETE FUNCTIONS ==========

    async def type_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for setting types (e.g., 'category', 'channel')."""
        return [
            app_commands.Choice(name=f"{type_name}", value=type_name)
            for type_name, info in self.SETTING_TYPES.items()
            if current.lower() in type_name.lower()
        ]

    async def name_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for setting names based on the selected type."""
        type_value = interaction.namespace.type
        if not type_value or type_value not in self.SETTING_TYPES:
            return []

        fields = self.SETTING_TYPES[type_value]["fields"]
        return [
            app_commands.Choice(name=f"{field_name}", value=field_name)
            for field_name, description in fields.items()
            if current.lower() in field_name.lower()
        ]

    # ========== HELPER METHODS ==========

    def _validate_setting(self, type_str: str, name_str: str) -> str | None:
        """Validates if the type and name exist in the configuration."""
        if type_str not in self.SETTING_TYPES:
            available = ", ".join(f"`{k}`" for k in self.SETTING_TYPES.keys())
            return f"❌ Invalid type `{type_str}`. Available types: {available}"
        if name_str not in self.SETTING_TYPES[type_str]["fields"]:
            available = ", ".join(f"`{k}`" for k in self.SETTING_TYPES[type_str]["fields"].keys())
            return f"❌ Invalid name `{name_str}` for type `{type_str}`. Available names: {available}"
        return None

    async def _validate_discord_object(self, interaction: Interaction, type_str: str, object_id: int) -> discord.abc.GuildChannel | None:
        """Validates that the given ID corresponds to a real Discord object."""
        if type_str == "category":
            return discord.utils.get(interaction.guild.categories, id=object_id)
        elif type_str == "channel":
            # This can find text, voice, etc.
            return discord.utils.get(interaction.guild.channels, id=object_id)
        return None

    # ========== SLASH COMMANDS ==========

    settings_group = app_commands.Group(name="setting", description="Manage server-specific bot settings.")

    @settings_group.command(name="add", description="Add a new setting configuration.")
    @app_commands.describe(
        type="The type of setting to add",
        name="The specific setting to configure",
        id="The Discord ID for this setting."
    )
    @app_commands.autocomplete(type=type_autocomplete, name=name_autocomplete)
    @moderator_required
    async def add_setting(self, interaction: Interaction, type: str, name: str, id: str):
        """Adds a new server setting."""
        await interaction.response.defer(ephemeral=True)

        # Validate setting type and name from our config
        validation_error = self._validate_setting(type, name)
        if validation_error:
            return await interaction.followup.send(validation_error, ephemeral=True)

        # Validate and convert ID
        try:
            setting_id = int(id)
        except ValueError:
            return await interaction.followup.send(f"❌ Invalid ID: `{id}`. Must be a numeric ID.", ephemeral=True)

        # Check if the setting already exists
        existing_value = await self.settings_service.get_setting_field(interaction.guild_id, type, name)
        if existing_value is not None:
            return await interaction.followup.send(f"❌ Setting `{type}.{name}` already exists. Use `/setting modify` to change it.", ephemeral=True)

        # Validate the Discord object exists
        discord_object = await self._validate_discord_object(interaction, type, setting_id)
        if not discord_object:
            return await interaction.followup.send(f"❌ A {type} with ID `{setting_id}` was not found in this server.", ephemeral=True)

        # Save to DB
        await self.settings_service.set_setting_field(interaction.guild_id, type, name, setting_id)

        embed = discord.Embed(
            title="✅ Setting Added",
            description=f"Successfully configured `{name}`.",
            color=discord.Color.green()
        )
        embed.add_field(name="Type", value=f"`{type}`", inline=True)
        embed.add_field(name="Name", value=f"`{name}`", inline=True)
        embed.add_field(name="Value", value=f"{discord_object.mention}\n`{setting_id}`", inline=True)
        embed.set_footer(text=f"Set by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @settings_group.command(name="modify", description="Modify an existing setting.")
    @app_commands.describe(
        type="The type of setting to modify.",
        name="The specific setting to change.",
        id="The new Discord ID for this setting."
    )
    @app_commands.autocomplete(type=type_autocomplete, name=name_autocomplete)
    @moderator_required
    async def modify_setting(self, interaction: Interaction, type: str, name: str, id: str):
        """Modifies an existing server setting."""
        await interaction.response.defer(ephemeral=True)

        validation_error = self._validate_setting(type, name)
        if validation_error:
            return await interaction.followup.send(validation_error, ephemeral=True)

        try:
            new_id = int(id)
        except ValueError:
            return await interaction.followup.send(f"❌ Invalid ID: `{id}`. Must be a numeric ID.", ephemeral=True)

        old_id = await self.settings_service.get_setting_field(interaction.guild_id, type, name)
        if old_id is None:
            return await interaction.followup.send(f"❌ Setting `{type}.{name}` does not exist. Use `/setting add` to create it.", ephemeral=True)

        if old_id == new_id:
            return await interaction.followup.send("ℹ️ The new ID is the same as the current one. No changes made.", ephemeral=True)

        new_discord_object = await self._validate_discord_object(interaction, type, new_id)
        if not new_discord_object:
            return await interaction.followup.send(f"❌ A {type} with ID `{new_id}` was not found in this server.", ephemeral=True)

        await self.settings_service.set_setting_field(interaction.guild_id, type, name, new_id)

        embed = discord.Embed(
            title="🔄 Setting Modified",
            description=f"Successfully updated `{name}`.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Type", value=f"`{type}`", inline=True)
        embed.add_field(name="Name", value=f"`{name}`", inline=True)
        embed.add_field(name="Previous Value", value=f"`{old_id}`", inline=False)
        embed.add_field(name="New Value", value=f"{new_discord_object.mention}\n`{new_id}`", inline=False)
        embed.set_footer(text=f"Modified by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @settings_group.command(name="remove", description="Remove a setting configuration.")
    @app_commands.describe(
        type="The type of setting to remove.",
        name="The specific setting to remove."
    )
    @app_commands.autocomplete(type=type_autocomplete, name=name_autocomplete)
    @moderator_required
    async def remove_setting(self, interaction: Interaction, type: str, name: str):
        """Removes a server setting."""
        await interaction.response.defer(ephemeral=True)

        validation_error = self._validate_setting(type, name)
        if validation_error:
            return await interaction.followup.send(validation_error, ephemeral=True)

        existing_value = await self.settings_service.get_setting_field(interaction.guild_id, type, name)
        if existing_value is None:
            return await interaction.followup.send(f"ℹ️ Setting `{type}.{name}` is not configured. Nothing to remove.", ephemeral=True)

        await self.settings_service.remove_setting_field(interaction.guild_id, type, name)

        embed = discord.Embed(
            title="🗑️ Setting Removed",
            description=f"Successfully removed the configuration for `{type}.{name}`.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Removed Setting", value=f"`{name}`", inline=True)
        embed.add_field(name="Previous Value", value=f"`{existing_value}`", inline=True)
        embed.set_footer(text=f"Removed by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @settings_group.command(name="list", description="List all configurable settings and their current values.")
    @moderator_required
    async def list_settings(self, interaction: Interaction):
        """Lists all available and configured server settings."""
        await interaction.response.defer(ephemeral=True)

        all_settings = await self.settings_service.get_all_settings(interaction.guild_id)

        embed = discord.Embed(
            title=f"⚙️ Settings for {interaction.guild.name}",
            description="Below are all available settings and their current configuration.",
            color=discord.Color.dark_gray()
        )

        for type_str, type_info in self.SETTING_TYPES.items():
            if not type_info["fields"]:
                continue

            value_list = []
            for name_str, description in type_info["fields"].items():
                current_value = all_settings.get(type_str, {}).get(name_str)

                if current_value:
                    # Try to resolve the ID to a mentionable object
                    obj = await self._validate_discord_object(interaction, type_str, current_value)
                    value_str = f"{obj.mention} (`{current_value}`)" if obj else f"**ID:** `{current_value}` (Not Found)"
                else:
                    value_str = "*Not Set*"

                value_list.append(f"**`{name_str}`**: {value_str}\n*↳ {description}*")

            if value_list:
                embed.add_field(
                    name=f"--- {type_info['name']} ---",
                    value="\n".join(value_list),
                    inline=False
                )

        if not embed.fields:
            embed.description = "There are no settings available to configure yet."

        await interaction.followup.send(embed=embed, ephemeral=True)

    @settings_group.command(name="change_ai_model", description="Change the active AI model for the server.")
    @moderator_required
    async def change_ai_model(self, interaction: Interaction):
        """Starts the guided flow to change the server's AI model."""
        try:
            currently_active_model = await self.settings_service.get_active_ai_model(interaction.guild_id)
            view = AIModelSelectionView(self.settings_service, interaction, currently_active_model)
            await view.start()
        except Exception as e:
            logger.error(f"Error in change_ai_model command: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while starting the selection process.", ephemeral=True)

async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(SettingsCog(bot))
    logger.info("SettingsCog loaded successfully.")

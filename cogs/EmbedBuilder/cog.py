import discord
import logging
from discord.ext import commands
from discord import app_commands

from .ui.main_panel.panel_view import MainPanelView
from .services.embed_service import EmbedService
from .services.button_action_engine import ButtonActionEngine
from .services.embed_sender import EmbedSender
from .utils.panel_manager import PanelManager
from config import EMBEDS_COLLECTION

logger = logging.getLogger(__name__)

class EmbedBuilderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # DatabaseManager instance
        self.embed_service = EmbedService(self.db)
        self.action_engine = ButtonActionEngine(self.embed_service)
        self.embed_sender = EmbedSender(self.embed_service, self.action_engine)
        self.panel_manager = PanelManager(self.embed_service, self.embed_sender)

        # Restore main panel view
        bot.add_view(MainPanelView(self.embed_service, self.embed_sender, self.panel_manager))

        # Restore all persistent embed views
        bot.loop.create_task(self._restore_persistent_embed_views())

    async def _restore_persistent_embed_views(self):
        """Rebuilds persistent views for all embeds with buttons across all guilds."""
        await self.bot.wait_until_ready()

        try:
            docs = await self.db.find_many(EMBEDS_COLLECTION, {})
            restored_count = 0

            for doc in docs:
                guild_id = doc["guild_id"]
                for embed_name, embed_data in doc.get("embeds", {}).items():
                    buttons = embed_data.get("config", {}).get("buttons", [])
                    if not buttons:
                        continue

                    try:
                        view = await self.action_engine.create_persistent_view(buttons)
                        self.bot.add_view(view)
                        restored_count += 1
                    except Exception as e:
                        logger.error(f"Failed to restore view for embed '{embed_name}' in guild {guild_id}: {e}")

            logger.info(f"✅ Restored {restored_count} persistent embed views on startup.")

        except Exception as e:
            logger.error(f"Error while restoring persistent embed views: {e}")

    @app_commands.command(name="embed_manager", description="Open the Embed Manager panel")
    async def embed_manager(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        existing = await self.embed_service.get_embed_panel(interaction.guild.id)
        if existing:
            try:
                channel = self.bot.get_channel(existing["channel_id"])
                await channel.fetch_message(existing["message_id"])
                await interaction.followup.send(
                    "ℹ️ Embed panel already exists in this server.",
                    ephemeral=True
                )
                return
            except (discord.NotFound, discord.Forbidden):
                await self.embed_service.delete_embed_panel(interaction.guild.id)

        # Create new panel
        embed = await self.panel_manager.build_embed_panel(interaction.guild.id)
        view = await MainPanelView.from_db(
            self.embed_service,
            self.embed_sender,
            self.panel_manager,
            interaction.guild.id
        )
        msg = await interaction.channel.send(embed=embed, view=view)
        await self.embed_service.save_embed_panel(interaction.guild.id, interaction.channel.id, msg.id)
        await interaction.followup.send("✅ Embed management panel created!", ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(EmbedBuilderCog(bot))

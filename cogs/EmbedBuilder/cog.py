import discord
import logging
from discord.ext import commands
from discord import app_commands

from .ui.main_panel.panel_view import BuilderView
from .services.embed_service import EmbedService
from .services.button_action_engine import ButtonActionEngine
from .services.embed_sender import EmbedSender
from .utils.panel_manager import PanelManager
from config import EMBEDS_COLLECTION

logger = logging.getLogger(__name__)

class EmbedBuilderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
        self.embed_service = EmbedService(self.db)
        self.action_engine = ButtonActionEngine(self.embed_service)
        self.embed_sender = EmbedSender(self.embed_service, self.action_engine)
        self.panel_manager = PanelManager(self.embed_service, self.embed_sender)

        # Restore the persistent Embed Builder panel view on startup
        bot.add_view(BuilderView(self.embed_service, self.embed_sender, self.panel_manager))

        # Restore all persistent embed views (for buttons on sent messages)
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

    @app_commands.command(name="embed_builder", description="Open the Embed Builder panel")
    async def embed_builder(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Check if the panel already exists, this logic is still valid
        existing = await self.embed_service.get_embed_panel(interaction.guild.id)
        if existing:
            try:
                channel = self.bot.get_channel(existing["channel_id"])
                await channel.fetch_message(existing["message_id"])
                await interaction.followup.send(
                    "ℹ️ Embed Builder panel already exists in this server.",
                    ephemeral=True
                )
                return
            except (discord.NotFound, discord.Forbidden):
                # If message was deleted, clean up the DB entry
                await self.embed_service.delete_embed_panel(interaction.guild.id)

        # Create the new static builder panel
        embed = await self.panel_manager.build_builder_embed()
        view = BuilderView(
            self.embed_service,
            self.embed_sender,
            self.panel_manager,
        )
        msg = await interaction.channel.send(embed=embed, view=view)

        # Save the location of the new panel
        await self.embed_service.save_embed_panel(interaction.guild.id, interaction.channel.id, msg.id)
        await interaction.followup.send("✅ Embed Builder panel created!", ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(EmbedBuilderCog(bot))

import discord
import logging
from discord.ext import commands
from discord import app_commands
from .ui.main_panel_view import MainPanelView
from .services.embed_service import EmbedService
from .utils.panel_manager import PanelManager

logger = logging.getLogger(__name__)

class EmbedBuilderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
        self.embed_service = EmbedService(self.db)
        self.panel_manager = PanelManager(self.embed_service)

        # Restore and Add persistent view
        bot.add_view(MainPanelView(self.embed_service, self.panel_manager))

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
        view = MainPanelView(self.embed_service, self.panel_manager)
        msg = await interaction.channel.send(embed=embed, view=view)
        await self.embed_service.save_embed_panel(interaction.guild.id, interaction.channel.id, msg.id)
        await interaction.followup.send("✅ Embed management panel created!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedBuilderCog(bot))

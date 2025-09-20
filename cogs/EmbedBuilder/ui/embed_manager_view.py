import discord
from discord.ui import View, Button, Select

from ..ui.attatch_channel_view import AttachChannelView
from .button_selection_view import ButtonSelectionView
from ..ui.embed_manager_modals import WebhookConfigModal

class ManageSingleEmbedView(View):
    """Panel for managing a single embed's tools."""

    def __init__(self, embed_name, embed_service, embed_sender):
        super().__init__(timeout=None)
        self.embed_name = embed_name
        self.embed_service = embed_service
        self.embed_sender = embed_sender

        # Row 0: Management
        self.add_item(AttachChannelButton(self.embed_service, self.embed_name))
        self.add_item(SendWithBotButton(self.embed_name, self.embed_service, self.embed_sender))
        self.add_item(SendWithWebhookButton(self.embed_name, self.embed_service, self.embed_sender))

        # Row 1: Button Actions
        self.add_item(ManageButtonActionsButton(self.embed_name, self.embed_service))


class AttachChannelButton(Button):
    def __init__(self, embed_service, embed_name):
        super().__init__(label="📌 Attach Channel", style=discord.ButtonStyle.primary)
        self.embed_service = embed_service
        self.embed_name = embed_name

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        attached = await self.embed_service.get_attached_channels(guild_id, self.embed_name)

        view = AttachChannelView(self.embed_service, self.embed_name, interaction.guild, attached)
        await interaction.response.send_message(
            "Select one or more channels to attach:",
            view=view,
            ephemeral=True
        )

class SendWithBotButton(Button):
    def __init__(self, embed_name: str, embed_service, embed_sender):
        super().__init__(label="🤖 Send with Bot", style=discord.ButtonStyle.secondary, row=0)
        self.embed_name = embed_name
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        # 1. Get attached channels from DB
        attached_channels = await self.embed_service.get_attached_channels(guild_id, self.embed_name)

        # 2. Use EmbedSender
        try:
            results = await self.embed_sender.send_embed(
                interaction=interaction,
                guild_id=guild_id,
                embed_name=self.embed_name,
                target_channels=attached_channels,
                method="bot"
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)
            return

        # 3. Build summary message
        success = [cid for cid, res in results.items() if res.startswith("sent")]
        failed = [f"<#{cid}> ({res})" for cid, res in results.items() if not res.startswith("sent")]

        if success:
            message = f"✅ Embed `{self.embed_name}` sent to {len(success)} channel(s)."
            if failed:
                message += f"\n❌ Failed in {len(failed)} channel(s):\n" + "\n".join(failed)
        else:
            message = f"❌ Failed to send embed `{self.embed_name}` anywhere.\n" + "\n".join(failed)

        await interaction.response.send_message(message, ephemeral=True)

class SendWithWebhookButton(Button):
    def __init__(self, embed_name: str, embed_service, embed_sender):
        super().__init__(label="🪝 Send with Webhook", style=discord.ButtonStyle.secondary, row=0)
        self.embed_name = embed_name
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            WebhookConfigModal(self.embed_name, self.embed_service, self.embed_sender)
        )

class ManageButtonActionsButton(Button):
    def __init__(self, embed_name: str, embed_service):
        super().__init__(label="🔧 Manage Button Actions", style=discord.ButtonStyle.secondary, row=1)
        self.embed_name = embed_name
        self.embed_service = embed_service

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        config_doc = await self.embed_service.get_embed_config(guild_id, self.embed_name)
        if not config_doc:
            await interaction.response.send_message(
                f"❌ No embed named `{self.embed_name}` found.",
                ephemeral=True
            )
            return

        buttons = config_doc.get("config", {}).get("buttons", [])
        if not buttons:
            await interaction.response.send_message(
                f"ℹ️ Embed `{self.embed_name}` has no buttons to configure.",
                ephemeral=True
            )
            return

        view = ButtonSelectionView(self.embed_name, buttons, self.embed_service)
        await interaction.response.send_message(view=view,ephemeral=True)

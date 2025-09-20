import discord
from discord.ui import View, ChannelSelect, Button

class AttachChannelView(View):
    def __init__(self, embed_service, embed_name, guild, attached, page=0, per_page=25):
        super().__init__(timeout=None)
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.guild = guild
        self.page = page
        self.per_page = per_page
        self.attached = attached

        self.add_item(ChannelMultiSelect(self.embed_service, self.embed_name, self.attached))

class ChannelMultiSelect(ChannelSelect):
    def __init__(self, embed_service, embed_name: str, attached: list[int]):
        self.embed_service = embed_service
        self.embed_name = embed_name

        # Convert attached channel IDs to SelectDefaultValue objects for default selection
        default_values = [discord.SelectDefaultValue(id=channel_id, type=discord.SelectDefaultValueType.channel) for channel_id in attached]

        super().__init__(
            placeholder="Select one or more channels to attach...",
            min_values=0,
            max_values=25,  # Discord's maximum for select menus
            channel_types=[discord.ChannelType.text],  # Only text channels for embed sending
            default_values=default_values,
            custom_id="embed:attach_channels"
        )

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        # Get selected channel IDs from the ChannelSelect values
        chosen_channels = [channel.id for channel in self.values]

        await self.embed_service.clear_channels(guild_id, self.embed_name)
        for channel_id in chosen_channels:
            await self.embed_service.attach_channel(guild_id, self.embed_name, channel_id)

        mentions = ", ".join(f"<#{cid}>" for cid in chosen_channels)

        # Create new view with updated attached channels
        new_view = AttachChannelView(
            self.embed_service,
            self.embed_name,
            interaction.guild,
            attached=chosen_channels
        )

        await interaction.response.edit_message(
            content=f"<:attachment:1417215411287494706> Embed `{self.embed_name}` is now attached to: {mentions if mentions else '`None`'}",
            view=new_view
        )

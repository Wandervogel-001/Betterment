import discord
from discord.ui import View, Select, Button

class AttachChannelView(View):
    def __init__(self, embed_service, embed_name, guild, page=0, per_page=25):
        super().__init__(timeout=60)
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.guild = guild
        self.page = page
        self.per_page = per_page

        channels = guild.text_channels
        start = page * per_page
        end = start + per_page
        sliced = channels[start:end]

        # Dropdown
        self.add_item(ChannelSelect(embed_service, embed_name, sliced, page))

        # Pagination Buttons
        if start > 0:
            self.add_item(PrevPageButton(embed_service, embed_name, guild, page))
        if end < len(channels):
            self.add_item(NextPageButton(embed_service, embed_name, guild, page))

class ChannelSelect(discord.ui.Select):
    def __init__(self, embed_service, embed_name, channels, page=0):
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.page = page

        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id))
            for ch in channels
        ]

        super().__init__(
            placeholder="Select a channel...",
            options=options,
            custom_id=f"attach_channel:{embed_name}:{page}"
        )

    async def callback(self, interaction: discord.Interaction):
        channel_id = int(self.values[0])
        guild_id = str(interaction.guild.id)

        await self.embed_service.attach_channel(guild_id, self.embed_name, channel_id)

        await interaction.response.send_message(
            f"📌 Embed `{self.embed_name}` attached to <#{channel_id}>",
            ephemeral=True
        )

class PrevPageButton(Button):
    def __init__(self, embed_service, embed_name, guild, page):
        super().__init__(label="⏮️ Prev", style=discord.ButtonStyle.secondary)
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.guild = guild
        self.page = page

    async def callback(self, interaction: discord.Interaction):
        view = AttachChannelView(self.embed_service, self.embed_name, self.guild, self.page - 1)
        await interaction.response.edit_message(view=view)


class NextPageButton(Button):
    def __init__(self, embed_service, embed_name, guild, page):
        super().__init__(label="⏭️ Next", style=discord.ButtonStyle.secondary)
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.guild = guild
        self.page = page

    async def callback(self, interaction: discord.Interaction):
        view = AttachChannelView(self.embed_service, self.embed_name, self.guild, self.page + 1)
        await interaction.response.edit_message(view=view)

import discord
from ..ui.main_panel_view import MainPanelView

class PanelManager:
    def __init__(self, embed_service, embed_sender):
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    async def build_embed_panel(self, guild_id: int) -> discord.Embed:
        """Builds the Embed Manager panel embed with registered embeds."""
        embeds = await self.embed_service.get_guild_embeds(str(guild_id))

        embed_panel = discord.Embed(
            title="📑 Embed Manager",
            description="Manage and create embeds for this server.",
            color=discord.Color.blurple()
        )

        if embeds:
            value = "\n".join([f"- `{name}`" for name in embeds.keys()])
            embed_panel.add_field(name="Registered Embeds", value=value, inline=False)
        else:
            embed_panel.add_field(
                name="Registered Embeds",
                value="*(No embeds registered yet)*",
                inline=False
            )

        embed_panel.set_footer(
            text="Use the buttons below to create, edit, and manage this server's embeds."
        )
        return embed_panel

    async def refresh_panel_embed(self, guild, message_id: int):
        """Fetches the saved panel and updates it with latest data."""
        panel_data = await self.embed_service.get_embed_panel(guild.id)
        if not panel_data:
            return None

        channel = guild.get_channel(panel_data["channel_id"])
        if not channel:
            return None

        try:
            msg = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            return None

        new_embed = await self.build_embed_panel(guild.id)
        view = MainPanelView(self.embed_service, self.embed_sender, self)
        await msg.edit(embed=new_embed, view=view)
        return msg

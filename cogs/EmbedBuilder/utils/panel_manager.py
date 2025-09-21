import discord
from ..ui.main_panel.panel_view import MainPanelView

class PanelManager:
    def __init__(self, embed_service, embed_sender):
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    async def build_embed_panel(self, guild_id: int, page: int = 0) -> discord.Embed:
        """Builds the Embed Manager panel embed with registered embeds for the specified page."""
        embeds = await self.embed_service.get_guild_embeds(str(guild_id))

        embed_panel = discord.Embed(
            title="📑 Embed Manager",
            description="Manage and create embeds for this server.",
            color=discord.Color(int("242429", 16))
        )

        if embeds:
            embed_names = list(embeds.keys())
            total = len(embed_names)
            per_page = 20  # 20 embeds per page (2 fields of 10 each)

            # Calculate the slice for current page
            start = page * per_page
            end = start + per_page
            paginated_embeds = embed_names[start:end]

            if paginated_embeds:
                # Split the paginated embeds into chunks of 10 for two fields
                chunks = [paginated_embeds[i:i + 10] for i in range(0, len(paginated_embeds), 10)]

                for idx, chunk in enumerate(chunks, start=1):
                    value = "\n".join([f"- `{name}`" for name in chunk])
                    embed_panel.add_field(
                        name=f"Registered Embeds {idx}",
                        value=value,
                        inline=True
                    )

                # Add pagination info to footer
                max_page = (total - 1) // per_page
                footer_text = f"Page {page + 1} of {max_page + 1} • Showing {len(paginated_embeds)} of {total} embeds"
            else:
                embed_panel.add_field(
                    name="Registered Embeds",
                    value="*(No embeds on this page)*",
                    inline=False
                )
                footer_text = f"Page {page + 1} • No embeds found"
        else:
            embed_panel.add_field(
                name="Registered Embeds",
                value="*(No embeds registered yet)*",
                inline=False
            )
            footer_text = "Use the buttons below to create, edit, and manage this server's embeds."

        embed_panel.set_footer(text=footer_text)
        return embed_panel

    async def build_panel_view(self, guild_id: int, page: int = 0, selected_embed: str = None) -> MainPanelView:
        """Builds the MainPanelView using the from_db factory method."""
        return await MainPanelView.from_db(
            embed_service=self.embed_service,
            embed_sender=self.embed_sender,
            panel_manager=self,
            guild_id=guild_id,
            page=page,
            selected_embed=selected_embed,
            attached_channels=None  # Let from_db handle loading attached channels if needed
        )

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

        # Build new embed and view (reset to page 0 on refresh)
        new_embed = await self.build_embed_panel(guild.id, page=0)
        new_view = await self.build_panel_view(guild.id, page=0)

        await msg.edit(embed=new_embed, view=new_view)
        return msg

    async def create_panel(self, guild, channel) -> discord.Message:
        """Creates a new embed management panel in the specified channel."""
        embed = await self.build_embed_panel(guild.id, page=0)
        view = await self.build_panel_view(guild.id, page=0)

        message = await channel.send(embed=embed, view=view)

        # Save panel data to database
        await self.embed_service.save_embed_panel(guild.id, channel.id, message.id)

        return message

    async def update_panel_with_selection(self, guild, message_id: int, selected_embed: str = None, page: int = 0):
        """Updates the panel with a specific embed selected and/or page."""
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

        # Build embed and view with specific selection/page
        new_embed = await self.build_embed_panel(guild.id, page=page)
        new_view = await self.build_panel_view(guild.id, page=page, selected_embed=selected_embed)

        await msg.edit(embed=new_embed, view=new_view)
        return msg

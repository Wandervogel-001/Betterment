import discord
from ..ui.embed_manager.manager_view import EmbedManagerView

PER_PAGE = 20  # up to 20 embeds per page (10 per column, 2 columns)

class PanelManager:
    def __init__(self, embed_service, embed_sender):
        self.embed_service = embed_service
        self.embed_sender = embed_sender

    async def build_builder_embed(self) -> discord.Embed:
        """Builds the static Embed Builder panel embed."""
        description = (
            "```\n"
            "╭────────────────────────────────────╮\n"
            "│            EMBED BUILDER           │\n"
            "╰────────────────────────────────────╯\n\n"
            " ✦ Welcome to the Embed Builder ✦\n"
            " Manage, edit, and create embeds.\n\n"
            " [1] ► [📁 Browse Embeds]\n"
            "       » Manage all existing embeds\n"
            "       » Edit safely in private mode\n\n"
            " [2] ► [➕ New Embed]\n"
            "       » Start a new creation\n"
            "       » Name it → editor opens\n"
            "```"
        )
        embed = discord.Embed(
            description=description,
            color=discord.Color(int("242429", 16))
        )
        return embed

    async def build_embed_panel(self, guild_id: int, page: int = 0) -> discord.Embed:
        """Builds the Embed Manager panel embed with registered embeds for the specified page."""
        embeds = await self.embed_service.get_guild_embeds(str(guild_id))
        embed_names = list(embeds.keys()) if embeds else []
        total = len(embed_names)

        # Pagination slice
        start = page * PER_PAGE
        end = start + PER_PAGE
        paginated_embeds = embed_names[start:end]

        embed_panel = discord.Embed(
            description=("```❖ Embed Manager ❖```"),
            color=discord.Color(int("242429", 16))
        )

        embed_panel.add_field(
            name="‎ ",
            value="```Registered Embeds```",
            inline=False
        )

        # Split embeds into 2 chunks of 10 each for inline columns
        if paginated_embeds:
            chunks = [paginated_embeds[i:i + 10] for i in range(0, len(paginated_embeds), 10)]
            for chunk in chunks:
                value = "\n".join([f"- `{name}`" for name in chunk])
                embed_panel.add_field(
                    name="‎ ",
                    value=value,
                    inline=True
                )
        else:
            embed_panel.add_field(
                name="‎ ",
                value="*(No embeds registered yet)*",
                inline=False
            )

        # Footer with pagination info
        if total > 0:
            max_page = (total - 1) // PER_PAGE
            footer_text = f"Page {page + 1} of {max_page + 1} • Showing {len(paginated_embeds)} of {total}"
        else:
            footer_text = "Page 1 of 1 • No embeds found"

        embed_panel.set_footer(text=footer_text)

        return embed_panel

    async def build_panel_view(self, guild_id: int, page: int = 0, selected_embed: str = None) -> EmbedManagerView:
        """Builds the EmbedManagerView using the from_db factory method."""
        return await EmbedManagerView.from_db(
            embed_service=self.embed_service,
            embed_sender=self.embed_sender,
            panel_manager=self,
            guild_id=guild_id,
            page=page,
            selected_embed=selected_embed,
            attached_channels=None
        )

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

        new_embed = await self.build_embed_panel(guild.id, page=page)
        new_view = await self.build_panel_view(guild.id, page=page, selected_embed=selected_embed)

        await msg.edit(embed=new_embed, view=new_view)
        return msg

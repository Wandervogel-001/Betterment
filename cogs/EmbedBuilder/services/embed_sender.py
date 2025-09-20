import discord


class EmbedSender:
    def __init__(self, embed_service, action_engine):
        self.embed_service = embed_service
        self.action_engine = action_engine

    async def send_embed(self, interaction: discord.Interaction,
                         guild_id: str, embed_name: str,
                         target_channels: list[int] = None,
                         method: str = "bot",
                         webhook_config: dict = None) -> dict:
        """Unified embed sending with persistent views"""
        embed, buttons_config = await self._build_embed_from_config(guild_id, embed_name)

        # Build view dynamically from buttons config
        view = await self.action_engine.create_persistent_view(buttons_config)

        if method == "bot":
            return await self._send_with_bot(interaction, embed, view, target_channels)
        elif method == "webhook":
            return await self._send_with_webhook(interaction, embed, view, target_channels, webhook_config)
        else:
            raise ValueError(f"Unsupported send method: {method}")

    async def _build_embed_from_config(self, guild_id: str, embed_name: str):
        """Fetch embed config from DB and return (discord.Embed, buttons_config)."""
        config_doc = await self.embed_service.get_embed_config(guild_id, embed_name)
        if not config_doc:
            raise ValueError(f"No embed named `{embed_name}` found.")

        embed_data = config_doc.get("config", {})
        buttons_config = embed_data.get("buttons", [])

        # Discord.Embed.from_dict requires clean data
        if "color" in embed_data and embed_data["color"] is None:
            del embed_data["color"]

        embed = discord.Embed.from_dict(embed_data)
        return embed, buttons_config

    async def _send_with_bot(self, interaction, embed, view, target_channels):
        """Send embed with bot identity (to multiple or current channel)."""
        results = {}
        guild = interaction.guild

        # If no attached channels → send in current channel
        if not target_channels:
            try:
                msg = await interaction.channel.send(embed=embed, view=view)
                results[interaction.channel.id] = f"sent to current channel ({msg.id})"
            except discord.Forbidden:
                results[interaction.channel.id] = "forbidden"
            except Exception as e:
                results[interaction.channel.id] = f"error: {str(e)}"
            return results

        # Else → send to all attached channels
        for channel_id in target_channels:
            channel = guild.get_channel(channel_id)
            if not channel:
                results[channel_id] = "channel not found"
                continue
            try:
                msg = await channel.send(embed=embed, view=view)
                results[channel_id] = f"sent ({msg.id})"
            except discord.Forbidden:
                results[channel_id] = "forbidden"
            except Exception as e:
                results[channel_id] = f"error: {str(e)}"
        return results

    async def _send_with_webhook(self, interaction, embed, view, target_channels, webhook_config):
        """Send embed with a temporary webhook in the target channels."""
        results = {}
        guild = interaction.guild

        # Required webhook config
        webhook_name = webhook_config.get("name") if webhook_config else "EmbedSender"
        avatar_bytes = webhook_config.get("avatar") if webhook_config else None

        # If no attached channels → send in current channel
        if not target_channels:
            try:
                webhook = await interaction.channel.create_webhook(
                    name=webhook_name,
                    avatar=avatar_bytes
                )
                msg = await webhook.send(embed=embed, view=view, username=webhook_name, wait=True)
                await webhook.delete()
                results[interaction.channel.id] = f"sent to current channel ({msg.id})"
            except discord.Forbidden:
                results[interaction.channel.id] = "forbidden (no webhook perms)"
            except Exception as e:
                results[interaction.channel.id] = f"error: {str(e)}"
            return results

        # Else → send to all attached channels
        for channel_id in target_channels:
            channel = guild.get_channel(channel_id)
            if not channel:
                results[channel_id] = "channel not found"
                continue
            try:
                webhook = await channel.create_webhook(
                    name=webhook_name,
                    avatar=avatar_bytes
                )
                msg = await webhook.send(embed=embed, view=view, username=webhook_name, wait=True)
                await webhook.delete()
                results[channel_id] = f"sent ({msg.id})"
            except discord.Forbidden:
                results[channel_id] = "forbidden (no webhook perms)"
            except Exception as e:
                results[channel_id] = f"error: {str(e)}"
        return results

import discord
from discord.ui import Modal, TextInput
import re
import aiohttp

class WebhookConfigModal(Modal, title="Webhook Configuration"):
    def __init__(self,  embed_name: str, embed_service, embed_sender):
        super().__init__()
        self.embed_service = embed_service
        self.embed_sender = embed_sender
        self.embed_name = embed_name

        self.webhook_name = TextInput(
            label="Webhook Name",
            placeholder="Enter the name for your webhook",
            required=True,
            max_length=80
        )
        self.add_item(self.webhook_name)

        self.avatar_url = TextInput(
            label="Avatar URL (Optional)",
            placeholder="Leave empty to use bot's avatar",
            required=False
        )
        self.add_item(self.avatar_url)

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        webhook_name = self.webhook_name.value.strip()
        avatar_url = self.avatar_url.value.strip() or None

        # Defer response — webhook ops may take time
        await interaction.response.defer(ephemeral=True)

        # 1. Fetch attached channels
        attached_channels = await self.embed_service.get_attached_channels(guild_id, self.embed_name)

        # 2. Fetch avatar bytes if provided
        avatar_bytes = None
        if avatar_url:
            try:
                avatar_bytes = await self._fetch_avatar(interaction, avatar_url)
            except Exception:
                pass  # silently ignore avatar errors

        # 3. Build webhook config
        webhook_config = {
            "name": webhook_name,
            "avatar": avatar_bytes
        }

        # 4. Send via EmbedSender
        try:
            results = await self.embed_sender.send_embed(
                interaction=interaction,
                guild_id=guild_id,
                embed_name=self.embed_name,
                target_channels=attached_channels,
                method="webhook",
                webhook_config=webhook_config
            )
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
            return

        # 5. Build summary
        success = [cid for cid, res in results.items() if res.startswith("sent")]
        failed = [f"<#{cid}> ({res})" for cid, res in results.items() if not res.startswith("sent")]

        if success:
            message = f"✅ Embed `{self.embed_name}` sent via webhook to {len(success)} channel(s)."
            if failed:
                message += f"\n❌ Failed in {len(failed)} channel(s):\n" + "\n".join(failed)
        else:
            message = f"❌ Failed to send embed `{self.embed_name}` via webhook anywhere.\n" + "\n".join(failed)

        await interaction.followup.send(message, ephemeral=True)

    async def _fetch_avatar(self, interaction: discord.Interaction, input_str: str) -> bytes:
        """Fetch avatar from a URL or a guild member mention (@id or @username)."""

        # 1. Check for mention by ID: <@user_id> or just user_id
        id_match = re.match(r"<@!?(\d+)>$|^(\d+)$", input_str)
        if id_match:
            user_id = int(id_match.group(1) or id_match.group(2))
            member = interaction.guild.get_member(user_id)
            if member:
                return await member.display_avatar.read()
            raise Exception(f"User with ID {user_id} not found in this guild.")

        # 2. Check for mention by username (exact match)
        username_match = re.match(r"^@(.+)$", input_str)
        if username_match:
            username = username_match.group(1)
            member = discord.utils.find(lambda m: m.name == username, interaction.guild.members)
            if member:
                return await member.display_avatar.read()
            raise Exception(f"User '{username}' not found in this guild.")

        # 3. Otherwise treat as URL
        # Normalize Discord proxy URLs → CDN links
        if "images-ext" in input_str and "cdn.discordapp.com" in input_str:
            idx = input_str.find("https/cdn.discordapp.com")
            if idx != -1:
                input_str = "https://" + input_str[idx + 6:]

        async with aiohttp.ClientSession() as session:
            async with session.get(input_str) as response:
                if response.status == 200:
                    return await response.read()
                raise Exception(f"Failed to fetch avatar: HTTP {response.status}")

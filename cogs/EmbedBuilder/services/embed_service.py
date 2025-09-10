from datetime import datetime
from typing import Dict, Any, Optional
from config import SETTINGS_COLLECTION

class EmbedService:
    def __init__(self, db):
        self.db = db

    # ========== SETTINGS: EMBED PANEL ==========

    async def save_embed_panel(self, guild_id: int, channel_id: int, message_id: int) -> bool:
        panel_data = {"channel_id": channel_id, "message_id": message_id}
        update_data = {"embed_manager_panel": panel_data, "updated_at": datetime.utcnow()}
        return await self.db.update_one(
            SETTINGS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )

    async def get_embed_panel(self, guild_id: int) -> Optional[Dict[str, Any]]:
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        return settings_doc.get("embed_manager_panel") if settings_doc else None

    async def delete_embed_panel(self, guild_id: int) -> bool:
        return await self.db.update_one(
            SETTINGS_COLLECTION,
            {"guild_id": guild_id},
            {"$unset": {"embed_manager_panel": ""}, "$set": {"updated_at": datetime.utcnow()}}
        )

    # ========== EMBED CONFIGS ==========

    async def get_guild_embeds(self, guild_id: str) -> Dict[str, dict]:
        doc = await self.db.find_one("embeds", {"guild_id": guild_id})
        return doc.get("embeds", {}) if doc else {}

    async def save_embed_config(self, guild_id: str, embed_name: str, config: dict):
        """Saves or updates an embed's configuration."""
        if 'buttons' not in config:
            config['buttons'] = []

        return await self.db.update_one(
            "embeds",
            {"guild_id": guild_id},
            {"$set": {f"embeds.{embed_name}.config": config}},
            upsert=True
        )

    async def delete_embed_entry(self, guild_id: str, embed_name: str):
        return await self.db.update_one(
            "embeds",
            {"guild_id": guild_id},
            {"$unset": {f"embeds.{embed_name}": ""}}
        )

    async def get_embed_config(self, guild_id: str, embed_name: str) -> Optional[dict]:
        doc = await self.db.find_one("embeds", {"guild_id": guild_id})
        if not doc or "embeds" not in doc or embed_name not in doc["embeds"]:
            return None
        return doc["embeds"].get(embed_name)

    # ========== CHANNEL ATTACHEMENT ==========

    async def attach_channel(self, guild_id: str, embed_name: str, channel_id: int) -> bool:
        """
        Attach (or re-attach) an embed to a specific channel.
        """
        update_data = {f"embeds.{embed_name}.channel_id": channel_id}
        return await self.db.update_one(
            "embeds",
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )

    async def detach_channel(self, guild_id: str, embed_name: str) -> bool:
        """
        Remove the channel attachment from an embed.
        """
        return await self.db.update_one(
            "embeds",
            {"guild_id": guild_id},
            {"$unset": {f"embeds.{embed_name}.channel_id": ""}}
        )

    async def get_attached_channel(self, guild_id: str, embed_name: str) -> Optional[int]:
        """
        Get the channel ID an embed is attached to (if any).
        """
        doc = await self.db.find_one("embeds", {"guild_id": guild_id})
        if not doc:
            return None

        embed_data = doc.get("embeds", {}).get(embed_name, {})
        return embed_data.get("channel_id")

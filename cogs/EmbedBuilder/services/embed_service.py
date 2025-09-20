from datetime import datetime
from typing import Dict, Any, Optional
from config import SETTINGS_COLLECTION, EMBEDS_COLLECTION
from discord import Embed, Color

class EmbedService:
    def __init__(self, db):
        self.db = db

    # ---- Settings: Embed Panel ----

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

    # ---- Embed configs ----

    async def get_guild_embeds(self, guild_id: str) -> Dict[str, dict]:
        doc = await self.db.find_one(EMBEDS_COLLECTION, {"guild_id": guild_id})
        return doc.get("embeds", {}) if doc else {}

    async def save_embed_config(self, guild_id: str, embed_name: str, config: dict):
        """Saves or updates an embed's configuration."""
        if 'buttons' not in config:
            config['buttons'] = []

        return await self.db.update_one(
            EMBEDS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": {f"embeds.{embed_name}.config": config}},
            upsert=True
        )

    async def delete_embed_entry(self, guild_id: str, embed_name: str):
        return await self.db.update_one(
            EMBEDS_COLLECTION,
            {"guild_id": guild_id},
            {"$unset": {f"embeds.{embed_name}": ""}}
        )

    async def get_embed_config(self, guild_id: str, embed_name: str) -> Optional[dict]:
        doc = await self.db.find_one(EMBEDS_COLLECTION, {"guild_id": guild_id})
        if not doc or "embeds" not in doc or embed_name not in doc["embeds"]:
            return None
        return doc["embeds"].get(embed_name)

    async def get_button_config(self, guild_id: str, custom_id: str) -> Optional[tuple[dict, str]]:
        doc = await self.db.find_one(EMBEDS_COLLECTION, {"guild_id": guild_id})
        if not doc or "embeds" not in doc:
            return None

        for embed_name, embed_data in doc["embeds"].items():
            buttons = embed_data.get("config", {}).get("buttons", [])
            for button in buttons:
                if button.get("custom_id") == custom_id:
                    return button, embed_name
        return None

    async def save_button_action(self, guild_id: str, embed_name: str, custom_id: str, action: dict):
        """Add or update an action for a button."""
        doc = await self.db.find_one(EMBEDS_COLLECTION, {"guild_id": guild_id})
        if not doc or "embeds" not in doc or embed_name not in doc["embeds"]:
            raise ValueError(f"Embed `{embed_name}` not found in guild {guild_id}")

        embed_config = doc["embeds"][embed_name]["config"]
        buttons = embed_config.get("buttons", [])

        # Find button by custom_id
        for button in buttons:
            if button["custom_id"] == custom_id:
                if "actions" not in button:
                    button["actions"] = []
                button["actions"].append(action)
                break
        else:
            raise ValueError(f"Button `{custom_id}` not found in embed `{embed_name}`")

        await self.db.update_one(
            EMBEDS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": {f"embeds.{embed_name}.config.buttons": buttons}}
        )

    async def list_button_actions(self, guild_id: str, embed_name: str, custom_id: str) -> list:
        """Return the actions list for a specific button inside an embed."""
        doc = await self.get_embed_config(guild_id, embed_name)
        if not doc:
            return []
        buttons = doc.get("config", {}).get("buttons", [])
        for b in buttons:
            if b.get("custom_id") == custom_id:
                return b.get("actions", []) or []
        return []

    async def update_button_actions(self, guild_id: str, embed_name: str, custom_id: str, new_actions: list) -> bool:
        """
        Replace actions array for the given button. If new_actions is empty, remove the actions key.
        Returns True on success.
        """
        # fetch doc
        doc = await self.db.find_one(EMBEDS_COLLECTION, {"guild_id": guild_id})
        if not doc or "embeds" not in doc or embed_name not in doc["embeds"]:
            raise ValueError(f"Embed `{embed_name}` not found for guild {guild_id}")

        buttons = doc["embeds"][embed_name]["config"].get("buttons", [])
        changed = False
        for b in buttons:
            if b.get("custom_id") == custom_id:
                if new_actions:
                    b["actions"] = new_actions
                else:
                    b.pop("actions", None)
                changed = True
                break

        if not changed:
            raise ValueError(f"Button `{custom_id}` not found in embed `{embed_name}`")

        # persist the updated buttons array back to the embed document
        update_path = {f"embeds.{embed_name}.config.buttons": buttons}
        ok = await self.db.update_one(EMBEDS_COLLECTION, {"guild_id": guild_id}, {"$set": update_path})
        return ok

    async def remove_button_action(self, guild_id: str, embed_name: str, custom_id: str, index: int):
        """Remove a specific action from a button by index."""
        doc = await self.db.find_one(EMBEDS_COLLECTION, {"guild_id": guild_id})
        if not doc or "embeds" not in doc or embed_name not in doc["embeds"]:
            raise ValueError(f"Embed `{embed_name}` not found in guild {guild_id}")

        buttons = doc["embeds"][embed_name]["config"].get("buttons", [])
        for button in buttons:
            if button["custom_id"] == custom_id:
                if "actions" in button and 0 <= index < len(button["actions"]):
                    button["actions"].pop(index)
                break

        await self.db.update_one(
            EMBEDS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": {f"embeds.{embed_name}.config.buttons": buttons}}
        )

    # ---- Channel attachment ----

    async def attach_channel(self, guild_id: str, embed_name: str, channel_id: int) -> bool:
        """
        Attach an embed to a channel (adds to list if not already attached).
        """
        field_path = f"embeds.{embed_name}.channels"
        return await self.db.update_one(
            EMBEDS_COLLECTION,
            {"guild_id": guild_id},
            {"$addToSet": {field_path: channel_id}},  # ensures no duplicates
            upsert=True
        )

    async def detach_channel(self, guild_id: str, embed_name: str, channel_id: int) -> bool:
        """
        Detach an embed from a specific channel.
        """
        field_path = f"embeds.{embed_name}.channels"
        return await self.db.update_one(
            EMBEDS_COLLECTION,
            {"guild_id": guild_id},
            {"$pull": {field_path: channel_id}}
        )

    async def clear_channels(self, guild_id: str, embed_name: str) -> bool:
        """
        Remove all channel attachments from an embed.
        """
        return await self.db.update_one(
            EMBEDS_COLLECTION,
            {"guild_id": guild_id},
            {"$unset": {f"embeds.{embed_name}.channels": ""}}
        )

    async def get_attached_channels(self, guild_id: str, embed_name: str) -> list[int]:
        """
        Get all channel IDs an embed is attached to.
        """
        doc = await self.db.find_one(EMBEDS_COLLECTION, {"guild_id": guild_id})
        if not doc:
            return []

        embed_data = doc.get("embeds", {}).get(embed_name, {})
        return embed_data.get("channels", [])

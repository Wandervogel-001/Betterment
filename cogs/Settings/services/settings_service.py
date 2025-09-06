import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import SETTINGS_COLLECTION, DEFAULT_AI_MODEL

logger = logging.getLogger(__name__)

class SettingsService:
    """
    Database service layer that provides team-specific operations
    using the generic DatabaseManager CRUD methods.
    """
    def __init__(self, db):
        self.db = db

    # ========== SETTINGS: AI MODEL ==========

    async def get_active_ai_model(self, guild_id: int) -> str:
        """Retrieves the active AI model for the guild, returning the default if not set."""
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        if settings_doc and "ai_model" in settings_doc:
            return settings_doc["ai_model"]
        return DEFAULT_AI_MODEL

    async def set_active_ai_model(self, guild_id: int, model_name: str) -> bool:
        """Sets the active AI model for the guild."""
        update_data = {"ai_model": model_name, "updated_at": datetime.utcnow()}
        return await self.db.update_one(
            SETTINGS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )

    # ========== SETTINGS: EXTENSIBLE CONFIGURATION SYSTEM ==========

    async def get_setting_object(self, guild_id: int, object_type: str) -> Dict[str, Any]:
        """Retrieves a settings object (categories or channels) from the guild's settings document."""
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        if settings_doc and object_type in settings_doc:
            return settings_doc[object_type]
        return {}

    async def get_setting_field(self, guild_id: int, object_type: str, field_name: str) -> Optional[Any]:
        """Retrieves a specific field from a settings object."""
        settings_object = await self.get_setting_object(guild_id, object_type)
        return settings_object.get(field_name)

    async def set_setting_field(self, guild_id: int, object_type: str, field_name: str, value: Any) -> bool:
        """Sets a specific field in a settings object."""
        update_data = {f"{object_type}.{field_name}": value, "updated_at": datetime.utcnow()}
        return await self.db.update_one(
            SETTINGS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )

    async def remove_setting_field(self, guild_id: int, object_type: str, field_name: str) -> bool:
        """Removes a specific field from a settings object."""
        return await self.db.update_one(
            SETTINGS_COLLECTION,
            {"guild_id": guild_id},
            {"$unset": {f"{object_type}.{field_name}": ""}, "$set": {"updated_at": datetime.utcnow()}}
        )

    async def get_all_settings(self, guild_id: int) -> Dict[str, Any]:
        """Retrieves the complete settings document for a guild."""
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        if not settings_doc:
            return {}

        # Remove internal fields from the returned data
        filtered_settings = {k: v for k, v in settings_doc.items()
                           if k not in ["_id", "guild_id", "created_at", "updated_at"]}
        return filtered_settings

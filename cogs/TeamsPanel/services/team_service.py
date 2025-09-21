import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import TEAMS_COLLECTION, UNREGISTERED_MEMBERS_COLLECTION, SETTINGS_COLLECTION

logger = logging.getLogger(__name__)

class TeamDatabaseService:
    """
    Database service layer that provides team-specific operations
    using the generic DatabaseManager CRUD methods.
    """
    def __init__(self, db):
        self.db = db

    # ========== TEAM MANAGEMENT ==========

    async def get_teams(self, guild_id: int) -> List[Dict[str, Any]]:
        """Retrieves all teams for a given guild."""
        return await self.db.find_many(TEAMS_COLLECTION, {"guild_id": guild_id})

    async def get_team_by_name(self, guild_id: int, team_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific team by its role name."""
        return await self.db.find_one(TEAMS_COLLECTION, {"guild_id": guild_id, "team_role": team_name})

    async def insert_team(self, team_data: Dict[str, Any]) -> Optional[str]:
        """Creates a new team document."""
        team_data.update({
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        return await self.db.insert_one(TEAMS_COLLECTION, team_data)

    async def delete_team(self, guild_id: int, team_role: str) -> bool:
        """Deletes a team document."""
        return await self.db.delete_one(TEAMS_COLLECTION, {"guild_id": guild_id, "team_role": team_role})

    async def update_team_field(self, guild_id: int, team_role: str, field: str, value: Any) -> bool:
        """Updates a specific field of a team document."""
        update_data = {field: value, "updated_at": datetime.utcnow()}
        return await self.db.update_one(
            TEAMS_COLLECTION,
            {"guild_id": guild_id, "team_role": team_role},
            {"$set": update_data}
        )

    async def update_team_members(self, guild_id: int, team_role: str, members_dict: Dict[str, Any]) -> bool:
        """Convenience method to update all members of a team."""
        return await self.update_team_field(guild_id, team_role, "members", members_dict)

    async def update_member_in_teams(self, guild_id: int, user_id: str, updates: Dict[str, Any]) -> int:
        """Updates specific fields for a member across all teams they might be in."""
        filter_query = {"guild_id": guild_id, f"members.{user_id}": {"$exists": True}}
        update_data = {f"members.{user_id}.{k}": v for k, v in updates.items()}
        update_data["updated_at"] = datetime.utcnow()
        return await self.db.update_many(TEAMS_COLLECTION, filter_query, {"$set": update_data})

    async def find_team_by_member(self, guild_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """Finds the team document that contains a specific member ID."""
        return await self.db.find_one(TEAMS_COLLECTION, {"guild_id": guild_id, f"members.{user_id}": {"$exists": True}})

    async def get_max_team_number(self, guild_id: int) -> int:
        """Finds the highest team_number for a guild for efficient numbering."""
        teams = await self.db.find_with_projection(
            TEAMS_COLLECTION,
            {"guild_id": guild_id},
            {"team_number": 1},
            sort=[("team_number", -1)]
        )
        return teams[0].get("team_number", 0) if teams else 0

    async def update_team_channel_name(self, guild_id: int, team_name: str, new_channel_name: str) -> bool:
        """Updates the channel name for a specific team."""
        return await self.update_team_field(guild_id, team_name, "channel_name", new_channel_name)

    # ========== UNREGISTERED MEMBER MANAGEMENT ==========

    async def get_unregistered_document(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves the single document containing all unregistered members for a guild."""
        return await self.db.find_one(UNREGISTERED_MEMBERS_COLLECTION, {"guild_id": guild_id})

    async def save_unregistered_member(self, guild_id: int, user_id: str, member_data: Dict, role_type: str) -> bool:
        """Saves or updates an unregistered member's data in the correct category (leaders/members)."""
        if role_type not in ["leaders", "members"]:
            raise ValueError("role_type must be 'leaders' or 'members'")

        update_data = {f"{role_type}.{user_id}": member_data, "updated_at": datetime.utcnow()}
        return await self.db.update_one(
            UNREGISTERED_MEMBERS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )

    async def remove_unregistered_member(self, guild_id: int, user_id: str) -> bool:
        """Removes a user from both unregistered leader and member lists in a single operation."""
        return await self.db.update_one(
            UNREGISTERED_MEMBERS_COLLECTION,
            {"guild_id": guild_id},
            {
                "$unset": {f"leaders.{user_id}": "", f"members.{user_id}": ""},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

    async def move_unregistered_member_role(self, guild_id: int, user_id: str, from_type: str, to_type: str) -> bool:
        """Atomically moves a member from one role type to another within the unregistered document."""
        if from_type not in ["leaders", "members"] or to_type not in ["leaders", "members"]:
            raise ValueError("role_type must be 'leaders' or 'members'")

        unregistered_doc = await self.get_unregistered_document(guild_id)
        if not unregistered_doc or user_id not in unregistered_doc.get(from_type, {}):
            logger.warning(f"User {user_id} not found in unregistered '{from_type}' list for guild {guild_id}.")
            return False

        member_data = unregistered_doc[from_type][user_id]

        update_pipeline = {
            "$set": {f"{to_type}.{user_id}": member_data, "updated_at": datetime.utcnow()},
            "$unset": {f"{from_type}.{user_id}": ""}
        }

        return await self.db.update_one(UNREGISTERED_MEMBERS_COLLECTION, {"guild_id": guild_id}, update_pipeline)

    # ========== SETTINGS: TEAM PANEL ==========

    async def save_team_panel(self, guild_id: int, channel_id: int, message_id: int) -> bool:
        """Saves or updates the team panel info within the guild's settings document."""
        panel_data = {"channel_id": channel_id, "message_id": message_id}
        update_data = {"team_panel": panel_data, "updated_at": datetime.utcnow()}
        return await self.db.update_one(
            SETTINGS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )

    async def get_team_panel(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves the team panel object from the guild's settings document."""
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        return settings_doc.get("team_panel") if settings_doc else None

    async def delete_team_panel(self, guild_id: int) -> bool:
        """Deletes the team panel object from the guild's settings document."""
        return await self.db.update_one(
            SETTINGS_COLLECTION,
            {"guild_id": guild_id},
            {"$unset": {"team_panel": ""}, "$set": {"updated_at": datetime.utcnow()}}
        )

    # ========== SETTINGS: MARATHON STATE ==========

    async def get_marathon_state(self, guild_id: int) -> bool:
        """Retrieves the marathon's active status from the guild's settings document."""
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        if settings_doc and "marathon_state" in settings_doc:
            return settings_doc["marathon_state"].get("is_active", False)
        return False

    async def set_marathon_state(self, guild_id: int, is_active: bool) -> bool:
        """Sets the marathon state within the guild's settings document."""
        state_data = {
            "is_active": is_active,
            "last_changed": datetime.utcnow()
        }
        update_data = {"marathon_state": state_data, "updated_at": datetime.utcnow()}
        result = await self.db.update_one(
            SETTINGS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )
        return result

    async def get_marathon_state_document(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves the marathon state object from the guild's settings document."""
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        return settings_doc.get("marathon_state") if settings_doc else None

    # ========== SETTINGS: COMMUNICATION CHANNEL ==========

    async def get_communication_channel_id(self, guild_id: int) -> Optional[int]:
        """Retrieves the communication channel ID from the guild's settings document."""
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        if settings_doc and "channel" in settings_doc:
            return settings_doc["channel"].get("communication_channel")
        return None

    async def get_setting_field(self, guild_id: int, section: str, field: str) -> Optional[int]:
        """
        Retrieves a nested field value from the guild's settings document.
        """
        settings_doc = await self.db.find_one(SETTINGS_COLLECTION, {"guild_id": guild_id})
        if not settings_doc:
            return None
        section_data = settings_doc.get(section, {})
        if not isinstance(section_data, dict):
            return None
        value = section_data.get(field)
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return value


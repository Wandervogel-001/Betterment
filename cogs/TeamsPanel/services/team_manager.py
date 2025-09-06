import logging
import re
import discord
from typing import Dict, List, Tuple, Optional
from ..models.team import Team, TeamError, TeamNotFoundError, InvalidTeamError, TeamMember, TeamConfig
from ..services.team_member_service import TeamMemberService
from ..services.team_validation import TeamValidator
from ..services.team_formation_service import TeamFormationService
from ..services.ai_handler import AIHandler
from ..services.scoring_engine import TeamScoringEngine
from ..utils import team_utils


logger = logging.getLogger(__name__)

class TeamManager:
    """
    Main entry point for team management. Consolidates team operations
    and provides a centralized database access point for all services.
    """

    def __init__(self, team_service):
        self.config = TeamConfig()
        self.team_service = team_service
        self.ai_handler = AIHandler(self.team_service)
        self.scorer = TeamScoringEngine(self.ai_handler)

        # Sub-services under manager ownership
        self.validator = TeamValidator(self.team_service)
        self.member_service = TeamMemberService(self.team_service, self.validator)
        self.formation_service = TeamFormationService(self.scorer, self.team_service, self)

    # ========== DIRECT TEAM OPERATIONS ==========

    def _get_member_role_title(self, member: discord.Member) -> str:
        """
        Gets the specific role title ("Team Leader", "Team Member", "Unregistered")
        for a given Discord member by checking their roles in real-time.
        The order of checks is important to assign the highest role.
        """
        # Create a set of role names for efficient lookup
        role_names = {role.name for role in member.roles}

        if "Team Leader" in role_names:
            return "Team Leader"
        if "Team Member" in role_names:
            return "Team Member"

        return "Unregistered"

    async def is_marathon_active(self, guild_id: int) -> bool:
        """Checks if marathon is currently active for a guild."""
        return await self.team_service.get_marathon_state(guild_id)

    async def get_marathon_state_info(self, guild_id: int) -> Dict:
        """
        Retrieves the full marathon state document, providing a default if none exists.
        """
        state_doc = await self.team_service.get_marathon_state_document(guild_id)
        if state_doc:
            return state_doc
        # Return a default structure if no state is found in the database
        return {"is_active": False, "last_changed": None}

    async def create_team(self, guild: discord.Guild, team_number: int, channel_name: str, member_mentions: str) -> Tuple[Team, List[str]]:
        """
        Creates a new team and returns the team object and a list of invalid member IDs that were skipped.
        """
        self.validator.validate_team_number(team_number)
        team_role = f"Team {team_number}"

        if await self.team_service.get_team_by_name(guild.id, team_role):
            raise InvalidTeamError(f"Team '{team_role}' already exists.")

        formatted_channel = self.validator.format_and_validate_channel_name(channel_name)
        member_ids = self.validator.parse_member_mentions(member_mentions)
        is_marathon = await self.is_marathon_active(guild.id)

        # We need to know which members were invalid to report back to the user
        valid_ids, invalid_ids, _ = await self.validator.filter_and_validate_members(guild, member_ids, 0, not is_marathon)

        if not valid_ids:
            # If no members are valid, raise a more descriptive error
            error_message = "No valid members were provided for the new team."
            if is_marathon and invalid_ids:
                 error_message = "No valid members were provided. During a marathon, all members must have the 'Team Member' or 'Team Leader' role."
            raise InvalidTeamError(error_message)

        members = await self.member_service.create_member_objects(guild, valid_ids, not is_marathon)
        team = Team(guild_id=guild.id, team_role=team_role, channel_name=formatted_channel, members=members, _team_number=team_number)

        await self.team_service.insert_team(team.to_dict())

        if is_marathon:
            await team_utils.provision_team_resources(guild, team)

        logger.info(f"Created team '{team_role}' with {len(members)} members. Skipped {len(invalid_ids)} invalid members.")

        # Return both the created team and the list of IDs that were skipped
        return team, invalid_ids

    async def get_team(self, guild_id: int, team_name: str) -> Team:
        """Retrieves a specific team by name."""
        team_data = await self.team_service.get_team_by_name(guild_id, team_name)
        if not team_data:
            raise TeamNotFoundError(f"Team '{team_name}' not found.")
        return team_utils.build_team_from_data(guild_id, team_data)

    async def get_all_teams(self, guild_id: int) -> List[Team]:
        """Retrieves all teams for a guild."""
        teams_data = await self.team_service.get_teams(guild_id)
        teams = [team_utils.build_team_from_data(guild_id, data) for data in teams_data]
        return sorted(teams, key=lambda t: t.team_number)

    async def delete_team_and_resources(self, guild: discord.Guild, team_name: str):
        """Deletes a team from the DB and removes its Discord role and channel."""
        team = await self.get_team(guild.id, team_name)
        deleted = await self.team_service.delete_team(guild.id, team_name)
        if deleted:
            await team_utils.cleanup_team_discord_resources(guild, team)
            return True
        else:
            raise TeamError(f"Failed to delete team '{team_name}' from the database.")

    async def update_team_channel_name(self, guild_id: int, team_name: str, new_channel_name: str) -> bool:
        """Updates the channel name for a specific team in the database."""
        formatted_name = self.validator.format_and_validate_channel_name(new_channel_name)
        result = await self.team_service.update_team_channel_name(guild_id, team_name, formatted_name)
        if result:
            logger.info(f"Successfully updated channel name for team '{team_name}' to '{formatted_name}'.")
            return True
        logger.warning(f"Attempted to update channel name for team '{team_name}' but no changes were made.")
        return False

    async def fetch_server_teams(self, guild: discord.Guild) -> dict:
        """Scans the server for existing team roles and registers them in the database."""
        registered_count = 0
        skipped_count = 0
        skipped_details = []

        existing_teams = {t.team_role for t in await self.get_all_teams(guild.id)}

        potential_team_roles = [
            r for r in guild.roles
            if (r.name.startswith("Team ") and
                not r.is_default() and
                r.name not in self.config.excluded_team_roles)
        ]

        for role in potential_team_roles:
            if role.name in existing_teams:
                skipped_count += 1
                skipped_details.append(f"`{role.name}` (already registered)")
                continue

            try:
                match = re.search(r"Team (\d+)", role.name)
                if not match:
                    skipped_details.append(f"`{role.name}` (invalid name format)")
                    continue
                team_number = int(match.group(1))
            except (ValueError, AttributeError):
                skipped_details.append(f"`{role.name}` (could not get team number)")
                continue

            found_channel = None
            for channel in guild.text_channels:
                overwrites = channel.overwrites_for(role)
                default_overwrites = channel.overwrites_for(guild.default_role)
                if overwrites.view_channel is True and default_overwrites.view_channel is False:
                    found_channel = channel
                    break

            if not found_channel:
                skipped_details.append(f"`{role.name}` (no private channel)")
                continue

            members_dict = {}
            for member in role.members:
                if not member.bot:
                    role_title = team_utils.get_member_role_title(member)
                    team_member = TeamMember(user_id=str(member.id), username=member.name, display_name=member.display_name, role_title=role_title)
                    members_dict[str(member.id)] = team_member

            if not members_dict:
                skipped_details.append(f"`{role.name}` (no valid members)")
                continue

            team_data = {
                "guild_id": guild.id,
                "team_number": team_number,
                "team_role": role.name,
                "channel_name": found_channel.name,
                "members": {uid: tm.to_dict() for uid, tm in members_dict.items()}
            }

            try:
                await self.team_service.insert_team(team_data)
                registered_count += 1
            except Exception as e:
                skipped_details.append(f"`{role.name}` (database error: {e})")

        return {"registered": registered_count, "skipped": skipped_count, "details": skipped_details}

    # ========== MEMBER OPERATIONS (delegated to services) ==========

    async def add_members_to_team(self, guild, team_name, member_mentions):
        """Orchestrates adding members by fetching team and marathon state first."""
        team = await self.get_team(guild.id, team_name)
        is_marathon = await self.is_marathon_active(guild.id)
        return await self.member_service.add_members_to_team(guild, team, member_mentions, is_marathon)

    async def remove_members_from_team(self, guild, team_name, member_ids):
        """Orchestrates removing members by fetching the team first."""
        team = await self.get_team(guild.id, team_name)
        return await self.member_service.remove_members_from_team(guild.id, team, member_ids)

    # ========== ORCHESTRATION METHODS ==========

    async def reflect_teams(self, guild: discord.Guild) -> Dict[str, List]:
        """
        Analyzes and reports on the consistency of team data by orchestrating
        calls to the team and member services.
        """
        teams = await self.get_all_teams(guild.id)
        empty_teams, no_leader_teams = [], []

        for team in teams:
            if not team.members:
                empty_teams.append(team.team_role)
                continue

            # This logic could be further delegated if needed
            _, has_leader = await self.member_service._update_team_members_data(guild, team.members)
            if not has_leader:
                no_leader_teams.append(team.team_role)

        # Get all members currently in a team to pass to the sync function
        all_team_member_ids = {uid for team in teams for uid in team.members.keys()}

        # Perform synchronization of unassigned members and get the report
        sync_report = await self.member_service.sync_unregistered_members(guild, all_team_member_ids)

        return {
            "empty_teams": empty_teams,
            "no_leader_teams": no_leader_teams,
            "unassigned_members": sync_report["unassigned_list"],
            "unassigned_leader_count": sync_report["leader_count"],
            "unassigned_member_count": sync_report["member_count"],
        }

    async def sync_database_with_discord(self, guild: discord.Guild) -> Dict:
        """
        Centralized method to synchronize the database with the current state of Discord.
        This is the single source of truth for data reflection.
        """
        try:
            report = await self.reflect_teams(guild)
            return report
        except Exception as e:
            logger.error(f"Error during data sync for guild {guild.id}: {e}", exc_info=True)
            return {}

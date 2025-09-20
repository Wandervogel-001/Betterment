import discord
from discord.ui import View, Button
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ButtonActionEngine:
    def __init__(self, embed_service):
        self.embed_service = embed_service

    async def process_button_interaction(self, interaction: discord.Interaction):
        """Global dispatcher for all button presses."""
        custom_id = None
        try:
            custom_id = interaction.data.get("custom_id")
        except Exception:
            pass

        if not custom_id:
            await self._safe_respond_text(interaction, "Invalid button.", ephemeral=True)
            return

        if not interaction.guild:
            await self._safe_respond_text(interaction, "This button must be used inside a server.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        result = await self.embed_service.get_button_config(guild_id, custom_id)
        if not result:
            await self._safe_respond_text(interaction, "This button is no longer valid.", ephemeral=True)
            return

        button_config, embed_name = result
        actions: List[Dict[str, Any]] = button_config.get("actions", []) or []

        if not actions:
            if self._response_available(interaction):
                try:
                    await interaction.response.defer(ephemeral=True)
                except Exception as e:
                    logger.debug(f"defer failed for {custom_id}: {e}")
                    await self._safe_respond_text(interaction, "Acknowledged.", ephemeral=True)
            return

        # Detect if this button involves embed actions
        has_embed_action = any(a.get("type") in ("send_embed", "edit_embed") for a in actions)

        results: List[str] = []
        errors: List[str] = []

        for action in actions:
            try:
                res = await self._execute_action(interaction, action, embed_name, has_embed_action)
                if res:
                    results.append(res)
            except Exception as e:
                logger.exception(f"Error executing action {action.get('type', 'unknown')}: {e}")
                errors.append(f"Failed to execute {action.get('type', 'unknown')}: {str(e)}")

        await self._send_action_response(interaction, results, errors, embed_name)

    async def _execute_action(self, interaction: discord.Interaction, action: dict, embed_name: str, has_embed_action: bool) -> Optional[str]:
        t = action.get("type")
        if t == "add_roles":
            return await self._execute_role_action(interaction, action, "add", embed_name, has_embed_action)
        elif t == "remove_roles":
            return await self._execute_role_action(interaction, action, "remove", embed_name, has_embed_action)
        elif t == "send_embed":
            return await self._execute_send_embed_action(interaction, action)
        elif t == "edit_embed":
            return await self._execute_edit_embed_action(interaction, action)
        else:
            logger.warning(f"Unknown action type: {t}")
            return f"Unknown action type: {t}"

    async def _execute_role_action(self, interaction: discord.Interaction, action: dict, operation: str, embed_name: str, has_embed_action: bool) -> Optional[str]:
        """Perform add/remove role operations.
        - Silent if combined with send_embed/edit_embed.
        - Otherwise, return a summary string for user feedback.
        """
        raw_role_ids = action.get("role_ids", []) or []
        role_ids = [self._parse_role_id(r) for r in raw_role_ids]
        role_ids = [r for r in role_ids if r is not None]

        if not role_ids:
            return None

        member = interaction.user
        guild = interaction.guild
        roles_to_process = []
        for rid in role_ids:
            role = guild.get_role(rid)
            if role and role < guild.me.top_role and not role.managed:
                roles_to_process.append(role)
            else:
                logger.debug(f"Skipping invalid/unmanageable role id {rid} for guild {guild.id}")

        if not roles_to_process:
            return None

        success_roles, failed_roles = [], []
        for role in roles_to_process:
            try:
                if operation == "add":
                    if role not in member.roles:
                        await member.add_roles(role, reason=f"Button action from embed '{embed_name}'")
                        success_roles.append(role)
                else:
                    if role in member.roles:
                        await member.remove_roles(role, reason=f"Button action from embed '{embed_name}'")
                        success_roles.append(role)
            except discord.Forbidden:
                logger.warning(f"Missing permission to modify role {role.name} for member {member}.")
                failed_roles.append(role)
            except Exception as e:
                logger.exception(f"Error processing role {getattr(role, 'name', role.id)}: {e}")
                failed_roles.append(role)

        # If this button also had embed actions, keep silent
        if has_embed_action:
            return None

        # Otherwise return a message so the user knows what happened
        parts = []
        if success_roles:
            role_names = [role.mention for role in success_roles]
            verb = "added" if operation == "add" else "removed"
            parts.append(f"**{verb.capitalize()} Roles:** {', '.join(role_names)}")

        if failed_roles:
            role_names = [role.mention for role in failed_roles]
            verb = "add" if operation == "add" else "remove"
            parts.append(f"**Failed to {verb}:** {', '.join(role_names)}")

        return " • ".join(parts) if parts else None

    async def _execute_send_embed_action(self, interaction: discord.Interaction, action: dict) -> Optional[str]:
        embed_names = action.get("embed_names", []) or []
        if not embed_names:
            return None

        guild_id = str(interaction.guild.id)

        embeds_to_send = []
        view_to_send: Optional[View] = None
        invalid_embeds = []

        # fetch only required embed configs (one query per embed)
        for en in embed_names:
            try:
                config_doc = await self.embed_service.get_embed_config(guild_id, en)
                if not config_doc:
                    invalid_embeds.append(en)
                    continue

                embed_data = config_doc.get("config", {}) or {}
                buttons_config = embed_data.get("buttons", [])

                # create view only if there's at least one button
                if view_to_send is None and buttons_config:
                    view_to_send = await self.create_persistent_view(buttons_config)

                # produce a clean embed dict without 'buttons'
                embed_clean = {k: v for k, v in embed_data.items() if k != "buttons"}
                if "color" in embed_clean and embed_clean["color"] is None:
                    del embed_clean["color"]

                embeds_to_send.append(discord.Embed.from_dict(embed_clean))
            except Exception as e:
                logger.exception(f"Error loading embed {en}: {e}")
                invalid_embeds.append(en)

        if not embeds_to_send:
            return "No valid embeds found to send"

        # Build kwargs but only include view if it's not None (fixes is_finished NoneType crash)
        kwargs = {"embeds": embeds_to_send[:10], "ephemeral": action.get("ephemeral", True)}
        if view_to_send is not None:
            kwargs["view"] = view_to_send

        # Try response first if available; otherwise use followup. Fallback to followup if response fails.
        try:
            if self._response_available(interaction):
                try:
                    await interaction.response.send_message(**kwargs)
                except discord.HTTPException as e:
                    # If response fails because interaction already acknowledged, fallback to followup
                    logger.debug(f"response.send_message failed, falling back to followup: {e}")
                    await interaction.followup.send(**kwargs)
            else:
                await interaction.followup.send(**kwargs)
        except Exception as e:
            logger.exception(f"Error sending embeds via response/followup: {e}")
            return f"Failed to send embeds: {str(e)}"

        # Return a small human result; the caller will filter embed results for summary.
        parts = [f"**Sent {len(embeds_to_send)} embed(s)**"]
        if invalid_embeds:
            parts.append(f"**{len(invalid_embeds)} embed(s) failed:** {', '.join(invalid_embeds)}")
        return " • ".join(parts)

    async def _execute_edit_embed_action(self, interaction: discord.Interaction, action: dict) -> Optional[str]:
        """Edit an existing message with a new embed and view (minimal fallbacks)."""
        embed_name = action.get("embed_name")
        if not embed_name:
            return "No target embed name configured for edit action."

        guild_id = str(interaction.guild.id)

        try:
            config_doc = await self.embed_service.get_embed_config(guild_id, embed_name)
            if not config_doc:
                return f"Failed to edit: Embed `{embed_name}` not found."

            embed_data = config_doc.get("config", {}) or {}
            buttons_config = embed_data.get("buttons", [])

            new_embed = discord.Embed.from_dict(
                {k: v for k, v in embed_data.items() if k != "buttons"}
            )
            new_view = await self.create_persistent_view(buttons_config) if buttons_config else None

            # 1) Preferred: edit via interaction.response (works on first use, ephemeral-safe)
            try:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=new_embed, view=new_view)
                    return None
            except Exception as e:
                logger.debug(f"interaction.response.edit_message failed: {e}")

            # 2) Fallback: edit the triggering message directly
            try:
                if interaction.message:
                    await interaction.message.edit(embed=new_embed, view=new_view)
                    return None
            except discord.Forbidden:
                logger.warning("Missing permissions to edit the target message.")
                return "Failed to edit message: Missing Permissions."
            except Exception as e:
                logger.debug(f"interaction.message.edit failed: {e}")

            # 3) Final fallback: send a followup message (ephemeral)
            try:
                await interaction.followup.send(embed=new_embed, view=new_view, ephemeral=True)
                return None
            except Exception as e:
                logger.exception(f"Final fallback followup for edit_embed failed: {e}")
                return "An error occurred while trying to edit the message."

        except discord.Forbidden:
            logger.warning(f"Missing permissions while fetching embed config for {embed_name}")
            return "Failed to edit message: Missing Permissions."
        except Exception as e:
            logger.exception(f"Error executing edit_embed action for {embed_name}: {e}")
            return "An error occurred while trying to edit the message."

    async def _send_action_response(self, interaction: discord.Interaction, results: List[str], errors: List[str],
                                    embed_name: str):
        """Send a summary for non-embed actions (role ops are silent)."""
        # Filter out embed send results (they already created visible messages)
        def is_embed_result(s: str) -> bool:
            return s and "embed(s)" in s

        summary_results = [r for r in results if r and not is_embed_result(r)]
        if not summary_results and not errors:
            return

        parts = []
        if summary_results:
            parts.extend(summary_results)
        if errors:
            parts.extend([f"**Error:** {e}" for e in errors])

        msg = "\n".join(parts)
        if not msg:
            return

        # Use response if available, otherwise followup
        try:
            if self._response_available(interaction):
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            logger.exception(f"Failed to send action summary for {embed_name}: {e}")

    async def create_persistent_view(self, buttons_config: List[dict]) -> View:
        """Create a runtime view from button config (lazy-loaded). Only create view if buttons present."""
        view = View(timeout=None)
        for button_data in buttons_config:
            style = button_data.get("style", "primary")
            label = button_data.get("label", "")
            url = button_data.get("url")
            custom_id = button_data.get("custom_id")

            bs = getattr(discord.ButtonStyle, style, None)
            if bs is None:
                bs = discord.ButtonStyle.primary

            if style == "link" or url:
                btn = Button(label=label, style=bs, url=url)
            else:
                btn = Button(label=label, style=bs, custom_id=custom_id)

                async def callback(interaction: discord.Interaction, cid=custom_id):
                    await self.process_button_interaction(interaction)

                btn.callback = callback

            view.add_item(btn)
        return view

    def _response_available(self, interaction: discord.Interaction) -> bool:
        """Safely check whether interaction.response exists and hasn't been used yet."""
        resp = getattr(interaction, "response", None)
        try:
            return resp is not None and not resp.is_done()
        except Exception:
            return False

    async def _safe_respond_text(self, interaction: discord.Interaction, text: str, ephemeral: bool = True):
        """Quick helper that replies with response if available, otherwise followup."""
        try:
            if self._response_available(interaction):
                await interaction.response.send_message(text, ephemeral=ephemeral)
            else:
                await interaction.followup.send(text, ephemeral=ephemeral)
        except Exception as e:
            logger.exception(f"Failed to send safe text response: {e}")

    def _parse_role_id(self, raw) -> Optional[int]:
        """Handle numeric ids or Mongo-exported {$numberLong: '...'} or strings."""
        try:
            if raw is None:
                return None
            if isinstance(raw, int):
                return raw
            if isinstance(raw, str):
                return int(raw)
            if isinstance(raw, dict):
                if "$numberLong" in raw:
                    return int(raw["$numberLong"])
                # try values
                for v in raw.values():
                    try:
                        return int(v)
                    except Exception:
                        continue
        except Exception:
            logger.debug(f"Failed to parse role id: {raw}")
        return None

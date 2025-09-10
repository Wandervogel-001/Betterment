import discord
from discord.ui import Modal, TextInput
import re
from datetime import datetime, timezone

class TitleDescModal(Modal, title="Edit Title, URL & Description"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], selected_field_index: int | None, selected_button_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.selected_field_index = selected_field_index
        self.selected_button_index = selected_button_index

        self.title_input = TextInput(label="Title", default=embed.title or "", required=False, max_length=256)
        self.add_item(self.title_input)
        self.url_input = TextInput(label="Title URL (Optional)", placeholder="e.g. https://discord.com", default=embed.url or "", required=False)
        self.add_item(self.url_input)
        self.desc_input = TextInput(label="Description", style=discord.TextStyle.paragraph, default=embed.description or "", required=False, max_length=4000)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView

        url_value = self.url_input.value.strip()

        self.embed.title = self.title_input.value
        self.embed.description = self.desc_input.value
        self.embed.url = url_value if url_value else None

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.selected_field_index,
                selected_button_index=self.selected_button_index
            )
        )

class ColorModal(Modal, title="Edit Embed Color"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], selected_field_index: int | None, selected_button_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.selected_field_index = selected_field_index
        self.selected_button_index = selected_button_index

        self.color_input = TextInput(label="Color", placeholder="e.g. #7289da, red, 0xFF5733", required=True, max_length=50)
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView
        color_str = self.color_input.value.strip()
        color = await self.parse_color(color_str)

        if not color:
            await interaction.response.send_message(f"❌ Invalid color format: `{color_str}`", ephemeral=True)
            return

        self.embed.color = color

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.selected_field_index,
                selected_button_index=self.selected_button_index
            )
        )

    async def parse_color(self, value: str) -> discord.Color | None:
        try:
            if value.startswith("#"):
                return discord.Color(int(value[1:], 16))
            if value.startswith("0x"):
                return discord.Color(int(value, 16))
            rgb_match = re.match(r"rgb\((\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\)", value, re.I)
            if rgb_match:
                r, g, b = map(int, rgb_match.groups())
                if all(0 <= v <= 255 for v in (r, g, b)):
                    return discord.Color.from_rgb(r, g, b)
            tuple_match = re.match(r"\(?\s*(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\s*\)?", value)
            if tuple_match:
                r, g, b = map(int, tuple_match.groups())
                if all(0 <= v <= 255 for v in (r, g, b)):
                    return discord.Color.from_rgb(r, g, b)
            if value.isdigit():
                return discord.Color(int(value))
            named = getattr(discord.Color, value.lower(), None)
            if callable(named):
                return named()
        except Exception:
            return None
        return None

class AddFieldModal(Modal, title="Add a New Field"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], selected_field_index: int | None, selected_button_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.selected_field_index = selected_field_index
        self.selected_button_index = selected_button_index

        self.field_name = TextInput(label="Field Name", placeholder="The title of the field", required=True, max_length=256)
        self.add_item(self.field_name)
        self.field_value = TextInput(label="Field Value", style=discord.TextStyle.paragraph, placeholder="The content of the field", required=True, max_length=1024)
        self.add_item(self.field_value)
        self.field_inline = TextInput(label="Inline? (yes/no)", placeholder="Default is 'yes'.", required=False, max_length=3)
        self.add_item(self.field_inline)

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView
        if len(self.embed.fields) >= 25:
            await interaction.response.send_message("❌ **Limit Reached:** You cannot have more than 25 fields.", ephemeral=True)
            return

        name = self.field_name.value
        value = self.field_value.value
        inline = self.field_inline.value.lower().strip() != 'no'
        self.embed.add_field(name=name, value=value, inline=inline)

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.selected_field_index,
                selected_button_index=self.selected_button_index
            )
        )

class EditFieldModal(Modal, title="Edit Field"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], field_index: int, selected_button_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.field_index = field_index
        self.selected_button_index = selected_button_index
        field = self.embed.fields[self.field_index]

        self.field_name = TextInput(label="Field Name", default=field.name, required=True, max_length=256)
        self.add_item(self.field_name)
        self.field_value = TextInput(label="Field Value", style=discord.TextStyle.paragraph, default=field.value, required=True, max_length=1024)
        self.add_item(self.field_value)
        self.field_inline = TextInput(label="Inline? (yes/no)", default="yes" if field.inline else "no", required=False, max_length=3)
        self.add_item(self.field_inline)

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView
        name = self.field_name.value
        value = self.field_value.value
        inline = self.field_inline.value.lower().strip() != 'no'
        self.embed.set_field_at(index=self.field_index, name=name, value=value, inline=inline)

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.field_index,
                selected_button_index=self.selected_button_index
            )
        )

class ImageModal(Modal, title="Set Thumbnail & Image"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], selected_field_index: int | None, selected_button_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.selected_field_index = selected_field_index
        self.selected_button_index = selected_button_index

        thumbnail_default = embed.thumbnail.url if embed.thumbnail else ""
        image_default = embed.image.url if embed.image else ""

        self.thumbnail_url = TextInput(label="Thumbnail URL", placeholder="Leave empty to remove. e.g. https://.../thumb.png", default=thumbnail_default, required=False)
        self.add_item(self.thumbnail_url)
        self.image_url = TextInput(label="Image URL (the large one)", placeholder="Leave empty to remove. e.g. https://.../image.png", default=image_default, required=False)
        self.add_item(self.image_url)

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView
        thumb_url = self.thumbnail_url.value.strip()
        img_url = self.image_url.value.strip()
        self.embed.set_thumbnail(url=thumb_url if thumb_url else None)
        self.embed.set_image(url=img_url if img_url else None)

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.selected_field_index,
                selected_button_index=self.selected_button_index
            )
        )

class AuthorModal(Modal, title="Set Embed Author"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], selected_field_index: int | None, selected_button_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.selected_field_index = selected_field_index
        self.selected_button_index = selected_button_index

        author_name_default = embed.author.name if embed.author and embed.author.name is not None else ""
        author_url_default = embed.author.url if embed.author and embed.author.url is not None else ""
        author_icon_url_default = embed.author.icon_url if embed.author and embed.author.icon_url is not None else ""

        self.author_name = TextInput(label="Author Name", placeholder="Leave empty to remove the author field.", default=author_name_default, required=False, max_length=256)
        self.add_item(self.author_name)
        self.author_url = TextInput(label="Author URL (Optional)", placeholder="A URL to link the author's name to.", default=author_url_default, required=False)
        self.add_item(self.author_url)
        self.author_icon_url = TextInput(label="Author Icon URL (Optional)", placeholder="A URL for the small icon next to the name.", default=author_icon_url_default, required=False)
        self.add_item(self.author_icon_url)

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView
        name = self.author_name.value.strip()
        url = self.author_url.value.strip()
        icon_url = self.author_icon_url.value.strip()

        if not name:
            self.embed.remove_author()
        else:
            self.embed.set_author(name=name, url=url if url else None, icon_url=icon_url if icon_url else None)

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.selected_field_index,
                selected_button_index=self.selected_button_index
            )
        )

class FooterModal(Modal, title="Set Embed Footer"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], selected_field_index: int | None, selected_button_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.selected_field_index = selected_field_index
        self.selected_button_index = selected_button_index

        # Get default values, handling cases where they might not exist
        footer_text_default = embed.footer.text if embed.footer and embed.footer.text else ""
        footer_icon_default = embed.footer.icon_url if embed.footer and embed.footer.icon_url else ""
        timestamp_default = embed.timestamp.strftime('%d/%m/%Y, %H:%M') if embed.timestamp else ""

        self.footer_text = TextInput(
            label="Footer Text",
            placeholder="Leave empty to remove footer elements.",
            default=footer_text_default,
            required=False,
            max_length=2048
        )
        self.add_item(self.footer_text)

        self.footer_icon_url = TextInput(
            label="Footer Icon URL (Optional)",
            placeholder="URL for the icon next to the footer text.",
            default=footer_icon_default,
            required=False
        )
        self.add_item(self.footer_icon_url)

        self.timestamp = TextInput(
            label="Timestamp (Optional)",
            placeholder="today, 10/09/2025, 11/09/2025, 18:50, or UNIX",
            default=timestamp_default,
            required=False
        )
        self.add_item(self.timestamp)

    def _parse_timestamp(self, value: str) -> datetime | None:
        """Parses a string into a timezone-aware datetime object."""
        value = value.strip().lower()
        if not value:
            return None

        if value == "today":
            return datetime.now(timezone.utc)

        if value.isdigit():
            try:
                # Convert UNIX timestamp to datetime object
                return datetime.fromtimestamp(int(value), tz=timezone.utc)
            except (ValueError, OSError):
                return None # Handles invalid or out-of-range timestamps

        # Try parsing combined and date-only formats
        formats_to_try = ['%d/%m/%y, %H:%M', '%d/%m/%Y, %H:%M', '%d/%m/%y', '%d/%m/%Y']
        for fmt in formats_to_try:
            try:
                dt_naive = datetime.strptime(value, fmt)
                # Make the datetime object timezone-aware (UTC)
                return dt_naive.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return None # Return None if all parsing attempts fail

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView

        text = self.footer_text.value.strip()
        icon_url = self.footer_icon_url.value.strip()
        timestamp_str = self.timestamp.value.strip()

        parsed_timestamp = self._parse_timestamp(timestamp_str)

        # If the user provided a timestamp string but it couldn't be parsed, show an error.
        if timestamp_str and parsed_timestamp is None:
            await interaction.response.send_message(
                f"❌ **Invalid Timestamp Format:** `{timestamp_str}`\n"
                "Please use one of these formats:\n"
                "• `today`\n"
                "• `dd/mm/yyyy` (e.g., `10/09/2025`)\n"
                "• `dd/mm/yyyy, HH:MM` (e.g., `11/09/2025, 18:50`)\n"
                "• A UNIX timestamp (e.g., `1757523955`)",
                ephemeral=True
            )
            return

        # Set the footer text and icon URL
        self.embed.set_footer(
            text=text if text else None,
            icon_url=icon_url if icon_url else None
        )

        # Set the timestamp directly on the embed object
        self.embed.timestamp = parsed_timestamp

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.selected_field_index,
                selected_button_index=self.selected_button_index
            )
        )

class AddButtonModal(Modal, title="Add a New Button"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], selected_field_index: int | None, selected_button_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.selected_field_index = selected_field_index
        self.selected_button_index = selected_button_index

        self.label = TextInput(label="Label", placeholder="Text displayed on the button", max_length=80, required=True)
        self.add_item(self.label)

        self.style = TextInput(label="Style", placeholder="primary, secondary, success, danger, or link", required=True)
        self.add_item(self.style)

        self.custom_id_or_url = TextInput(label="Custom ID or URL (if style is link)", placeholder="A unique ID, or https://...", required=True)
        self.add_item(self.custom_id_or_url)

        self.row = TextInput(label="Row (0-4, optional)", placeholder="Leave empty for auto-placement", required=False)
        self.add_item(self.row)

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView

        if len(self.buttons) >= 25:
            await interaction.response.send_message("❌ **Limit Reached:** You cannot have more than 25 buttons.", ephemeral=True)
            return

        style_str = self.style.value.lower().strip()
        valid_styles = {"primary": 1, "secondary": 2, "success": 3, "danger": 4, "link": 5}
        if style_str not in valid_styles:
            await interaction.response.send_message(f"❌ **Invalid Style:** Style must be one of `primary`, `secondary`, `success`, `danger`, or `link`.", ephemeral=True)
            return

        button_style = discord.ButtonStyle(valid_styles[style_str])
        url = None
        custom_id = None

        if button_style == discord.ButtonStyle.link:
            url = self.custom_id_or_url.value.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                 await interaction.response.send_message(f"❌ **Invalid URL:** The URL must start with `http://` or `https://` for link buttons.", ephemeral=True)
                 return
        else:
            custom_id = self.custom_id_or_url.value.strip()

        row_val = self.row.value.strip()
        row = None
        if row_val:
            try:
                row = int(row_val)
                if not 0 <= row <= 4: raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ **Invalid Row:** Row must be a number between 0 and 4.", ephemeral=True)
                return

        new_button = {"label": self.label.value, "style": style_str, "custom_id": custom_id, "url": url, "row": row}
        self.buttons.append(new_button)

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.selected_field_index,
                selected_button_index=self.selected_button_index
            )
        )

class EditButtonModal(Modal, title="Edit a Button"):
    def __init__(self, embed_service, embed_name: str, embed: discord.Embed, buttons: list[dict], button_index: int, selected_field_index: int | None):
        super().__init__()
        self.embed_service = embed_service
        self.embed_name = embed_name
        self.embed = embed
        self.buttons = buttons
        self.button_index = button_index
        self.selected_field_index = selected_field_index
        button_data = self.buttons[self.button_index]

        self.label = TextInput(label="Label", default=button_data.get('label'), max_length=80, required=True)
        self.add_item(self.label)

        self.style = TextInput(label="Style", default=button_data.get('style'), placeholder="primary, secondary, success, danger, or link", required=True)
        self.add_item(self.style)

        id_or_url = button_data.get('custom_id') or button_data.get('url')
        self.custom_id_or_url = TextInput(label="Custom ID or URL (if style is link)", default=id_or_url, placeholder="A unique ID, or https://...", required=True)
        self.add_item(self.custom_id_or_url)

        row_val = button_data.get('row')
        self.row = TextInput(label="Row (0-4, optional)", default=str(row_val) if row_val is not None else "", placeholder="Leave empty for auto-placement", required=False)
        self.add_item(self.row)

    async def on_submit(self, interaction: discord.Interaction):
        from .embed_editor_view import EmbedEditorView

        style_str = self.style.value.lower().strip()
        valid_styles = {"primary": 1, "secondary": 2, "success": 3, "danger": 4, "link": 5}
        if style_str not in valid_styles:
            await interaction.response.send_message(f"❌ **Invalid Style:** Style must be one of `primary`, `secondary`, `success`, `danger`, or `link`.", ephemeral=True)
            return

        button_style = discord.ButtonStyle(valid_styles[style_str])
        url = None
        custom_id = None

        if button_style == discord.ButtonStyle.link:
            url = self.custom_id_or_url.value.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                 await interaction.response.send_message(f"❌ **Invalid URL:** The URL must start with `http://` or `https://` for link buttons.", ephemeral=True)
                 return
        else:
            custom_id = self.custom_id_or_url.value.strip()

        row_val = self.row.value.strip()
        row = None
        if row_val:
            try:
                row = int(row_val)
                if not 0 <= row <= 4: raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ **Invalid Row:** Row must be a number between 0 and 4.", ephemeral=True)
                return

        updated_button = {"label": self.label.value, "style": style_str, "custom_id": custom_id, "url": url, "row": row}
        self.buttons[self.button_index] = updated_button

        await interaction.response.edit_message(
            embed=self.embed,
            view=EmbedEditorView(
                self.embed_service,
                self.embed_name,
                self.embed,
                buttons=self.buttons,
                selected_field_index=self.selected_field_index,
                selected_button_index=self.button_index
            )
        )

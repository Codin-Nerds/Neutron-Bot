import json
import textwrap
import typing as t

from discord import Attachment, Color, Embed, Message, NotFound
from discord.ext.commands import Cog
from loguru import logger

from bot.core.bot import Bot


class FilePaste(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def upload_attachments(self, attachments: t.List[Attachment], max_file_size: int = 500_000) -> t.Optional[str]:
        """
        Try to upload given `attachments` to paste.gg service.

        Attachments which doesn't follow UTF-8 encoding will be ignored.
        Attachments which weren't found (were already removed) will be ignored.
        Attachments over `max_file_size` (defaults to 500KB) will be ignored.
        If there aren't any applicable attachments to be uploaded, return None.
        Otherwise return URL to the uploaded content of given attachments.
        """

        upload_files = []
        for attachment in attachments:
            # Don't try loading files over maximum size
            if attachment.size > max_file_size:
                logger.debug(f"Attachment {attachment.filename} skipped, maximum size surpassed ({attachment.size} > {max_file_size})")
                continue

            try:
                content = await attachment.read()
                value = content.decode("utf-8")
            except (NotFound, UnicodeDecodeError):
                continue
            else:
                upload_files.append({
                    "name": attachment.filename,
                    "content": {
                        "format": "text",
                        "value": value
                    }
                })

        if len(upload_files) == 0:
            return

        payload = {
            "name": "Automatic attachment paste.",
            "description": "This paste was automatically generated from a discord message attachment.",
            "files": upload_files
        }
        try:
            response = await self.bot.http_session.post(
                "https://api.paste.gg/v1/pastes",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload)
            )
        except ConnectionError:
            logger.warning("Failed to paste content to paste.gg, Ended with ConnectionError.")
            return

        if response.status != 201:
            logger.warning(f"Failed to paste content to paste.gg, ended with {response.status}.")
            return
        json_response = await response.json()
        paste_id = json_response["result"]["id"]
        return f"https://www.paste.gg/{paste_id}"

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """
        Automatically remove non-whitelisted file attachments and try to upload them to hastebin.
        This doesn't affect DMs or people with manage_messages permissions

        This is here for security reasons, because we usually don't want
        people uploading `.exe`/`.bat` or similar executable files.
        """
        if not message.attachments or not message.guild:
            return

        if message.author.permissions_in(message.channel).manage_messages:
            return

        # TODO: Make per-guild database for this
        allowed_extensions = {
            # Videos
            "3gp", "avi", "mkv", "mov", "mp4", "mpeg", "gif", "wmv",
            # Photos
            "h264", "jpg", "jepg", "png", "svg", "psd", "bmp",
            # Music
            "mp3", "wav", "ogg"
        }

        affected_attachments = []
        for attachment in message.attachments:
            split_name = attachment.filename.lower().split(".")
            extension = "txt" if len(split_name) < 2 else split_name[-1]  # Default to txt if extension wasn't found

            if extension in allowed_extensions:
                continue

            logger.debug(f"User <@{message.author.id}> posted a message on {message.guild.id} with protected attachments ({extension})")
            affected_attachments.append(attachment)

        url = await self.upload_attachments(affected_attachments)

        embed = Embed(
            title="Your message got zapped by our spam filter.",
            description=textwrap.dedent(
                """
                We don't allow posting file attachments, here are some tips which might help you:
                • Try shortening your message, discord limit is 2000 characters.
                • Use a paste service such as `paste.gg` or similar service.
                • Split your message into multiple parts (pasting is usually a better option).
                """
            ),
            color=Color.red()
        )

        if url is not None:
            embed.add_field(
                name="Automatic attachment upload",
                value=textwrap.dedent(
                    f"""
                    We took care of uploading the file for you, since we know it can be tedious.
                    You can find your file on `paste.gg` paste service under this link:
                    **--> {url}**
                    """
                ),
                inline=False
            )

        await message.channel.send(f"Hey {message.author.mention}", embed=embed)
        await message.delete()


def setup(bot: Bot) -> None:
    bot.add_cog(FilePaste(bot))

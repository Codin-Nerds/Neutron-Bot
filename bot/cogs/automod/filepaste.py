import textwrap

from discord import Color, Embed, Message
from discord.ext.commands import Cog
from loguru import logger

from bot.core.bot import Bot
from bot.utils.paste_upload import upload_attachments


class FilePaste(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

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

        if len(affected_attachments) == 0:
            return

        url = await upload_attachments(self.bot.http_session, affected_attachments)

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

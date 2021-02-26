import typing as t

from discord import Color, Embed, Guild, Message
from discord.ext.commands import Cog
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.utils.paste_upload import upload_attachments, upload_files, upload_text


class MessageLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_log(self, guild: Guild, *send_args, **send_kwargs) -> bool:
        """
        Try to send a log message to a message_log channel for given guild,
        args and kwargs to this function will be used in the actual `Channel.send` call.

        If the message was sent, return True, otherwise return False
        (might happen if message_log channel isn't defined in database).
        """
        mod_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "message_log", guild)
        mod_log_channel = guild.get_channel(mod_log_id)
        if mod_log_channel is None:
            return False

        await mod_log_channel.send(*send_args, **send_kwargs)
        return True

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message) -> None:
        # Ignore DMs
        if not after.guild:
            return

        if after.author.bot:
            return

        response = (
            f"**Author:** {after.author.mention}\n"
            f"**Channel:** {after.channel.mention}\n"
            f"**Message ID:** {after.id}"
        )

        # Limit log embed to 800 characters, to avoid huge messages
        # cluttering the log, if message is longer, upload it instead.
        if len(before.clean_content + after.clean_content) > 2000 - len(response):
            # NOTE; Text uploading might be happening too often, and might have to be removed
            # in the future
            payload = [
                {
                    "name": "before",
                    "content": {
                        "format": "text",
                        "value": before.content
                    }
                },
                {
                    "name": "after",
                    "content": {
                        "format": "text",
                        "value": after.content
                    }
                },
            ]

            url = await upload_files(
                self.bot.http_session, payload,
                paste_name="Automatic message upload.",
                paste_description="This paste was automatically generated from edited discrod message."
            )
            if url:
                response += f"\n**Changes:** Message too long, check [message upload]({url})"
            else:
                response += "\n**Changes:** Message too long (WARNING: Automatic upload failed)"
        else:
            response += f"\n**Before:** {before.content}"
            response += f"\n**After:** {after.content}"

        response += f"\n[Jump link]({after.jump_url})"

        embed = Embed(
            title="Message edited",
            description=response,
            color=Color.dark_orange()
        )

        await self.send_log(after.guild, embed=embed)
        # TODO: Add this message to ignored, for on_raw_message_edit

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent) -> None:
        # TODO: Finish this
        pass

    @Cog.listener()
    async def on_message_delete(self, message: Message) -> None:
        # Ignore DMs
        if not message.guild:
            return

        if message.author.bot:
            return

        # TODO: Add ignore from automod/filepaste cog

        response = (
            f"**Author:** {message.author.mention}\n"
            f"**Channel:** {message.channel.mention}\n"
            f"**Message ID:** {message.id}"
        )

        if message.attachments:
            url = upload_attachments(self.bot.http_session, message.attachments)
            response += f"\n**Attachments:** {len(message.attachments)}"
            if url:
                response += f" [link]({url})"

        # Limit log embed to 800 characters, to avoid huge messages
        # cluttering the log, if message is longer, upload it instead.
        if len(message.clean_content) > 800 - len(response):
            # NOTE; Text uploading might be happening too often, and might have to be removed
            # in the future
            url = await upload_text(
                self.bot.http_session, message.content,
                file_name="message.md", paste_name="Automatic message upload.",
                paste_description="This paste was automatically generated from removed discrod message."
            )
            if url:
                response += f"\n**Content:** Message too long, check [message upload]({url})"
            else:
                response += "\n**Contet:** Message too long (WARNING: Automatic upload failed)"
        else:
            response += f"\n**Content:** {message.content}"

        response += f"\n[Jump link]({message.jump_url})"

        embed = Embed(
            title="Message deleted",
            description=response,
            color=Color.dark_orange()
        )

        await self.send_log(message.guild, embed=embed)
        # TODO: Add this message to ignored, for on_raw_message_deletes

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        # TODO: Finish this
        pass

    @Cog.listener()
    async def on_bulk_message_delete(self, messages: t.List[Message]) -> None:
        # Ignore DMs
        if not messages[0].guild:
            return

        if messages[0].author.bot:
            return

        # TODO: Ignore clean commands

        response = f"**Amount:** {len(messages)}"

        discovered_attachments = []
        for message in messages:
            for attachment in message.attachments:
                # We could upload here, but bulk deletion might capture many of these
                # and it's not worth to upload in these cases, bulk removal can't be initialized
                # by regular users anyway, so not knowing what was removed isn't a huge issue
                # since it was removed by ranked persion, for the same reason, we won't upload
                # the text of these messages either
                discovered_attachments.append(attachment.filename)
        response += f"**Attachments:** {len(discovered_attachments)}"

        response += f"\n[First message jump link]({message[0].jump_url})"

        embed = Embed(
            title="Bulk Message deletion",
            description=response,
            color=Color.dark_orange()
        )

        await self.send_log(message.guild, embed=embed)
        # TODO: Add this message to ignored, for on_raw_message_deletes

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        # TODO: Finish this
        pass


def setup(bot: Bot) -> None:
    bot.add_cog(MessageLog(bot))

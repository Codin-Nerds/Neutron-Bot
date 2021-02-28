import datetime
import textwrap
import typing as t

from discord import Color, Embed, Guild, Message
from discord.ext.commands import Cog
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent

from bot.config import Event
from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.utils.paste_upload import upload_attachments, upload_files, upload_text

# We should limit the maximum message size allowed for
# the embeds, to avoid huge embeds cluttering the message log
# for no reason, if they are over this size, we upload these
# messages to a paste service instead.
MAX_LOGGED_MESSAGE_SIZE = 800


class MessageLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    def is_ignored(self, message: Message, event: t.Optional[Event] = None) -> bool:
        """
        Determine if the listener should proceed, or if given message should be ignored.

        Ignored circumstances:
            * Message is a DM
            * Message was sent by a bot
            * Message was found in ignored list for given `event` (skipped if event isn't provided)

        If `True` is returned given message should be ignored, otherwise return `False`.
        """
        if not message.guild or message.author.bot:
            return True

        if event and self.bot.log_is_ignored(event, (message.guild.id, message.id)):
            return True

        return False

    async def send_log(self, guild: Guild, *send_args, **send_kwargs) -> bool:
        """
        Try to send a log message to a message_log channel for given guild,
        args and kwargs to this function will be used in the actual `Channel.send` call.

        If the message was sent, return True, otherwise return False
        (might happen if message_log channel isn't defined in database).
        """
        message_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "message_log", guild)
        message_log_channel = guild.get_channel(int(message_log_id))
        if message_log_channel is None:
            return False

        await message_log_channel.send(*send_args, **send_kwargs)
        return True

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message) -> None:
        """
        Send a log message whenever any sent message is edited.

        This is useful for moderation purposes, because users often try to hide what
        they send, to avoid getting caught breaking some rules, logging the content of
        these messages will prevent that.

        Messages can sometimes get quite long, and we don't want to clutter the log with them,
        if this is the case, we upload this message to a paste service and only provide a link.
        """
        if self.is_ignored(message=after, event=Event.message_edit):
            return

        # Add message to ignore list, to prevent raw event on executing
        self.bot.log_ignore(Event.message_edit, (after.guild.id, after.id))

        response = (
            f"**Author:** {after.author.mention}\n"
            f"**Channel:** {after.channel.mention}\n"
            f"**Message ID:** {after.id}"
        )

        # Limit log embed to avoid huge messages cluttering the log,
        # if message is longer, upload it instead.
        if len(before.clean_content + after.clean_content) > MAX_LOGGED_MESSAGE_SIZE:
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
                paste_description="This paste was automatically generated from edited discord message."
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
        embed.timestamp = datetime.datetime.utcnow()

        await self.send_log(after.guild, embed=embed)

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent) -> None:
        # TODO: Finish this
        pass

    @Cog.listener()
    async def on_message_delete(self, message: Message) -> None:
        """
        Send a log message whenever any sent message is removed.

        This is useful for moderation purposes, because users often try to hide what
        they send, to avoid getting caught breaking some rules, logging the content of
        these messages will prevent that.

        Messages can sometimes get quite long, and we don't want to clutter the log with them,
        if this is the case, we upload this message to a paste service and only provide a link.
        """
        if self.is_ignored(message, Event.message_delete):
            return

        # Add message to ignore list, to prevent raw event on executing
        self.bot.log_ignore(Event.message_delete, (message.guild.id, message.id))

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

        # Limit log embed to avoid huge messages cluttering the log,
        # if message is longer, upload it instead.
        if len(message.clean_content) > MAX_LOGGED_MESSAGE_SIZE:
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
        embed.timestamp = datetime.datetime.utcnow()

        await self.send_log(message.guild, embed=embed)

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        # TODO: Finish this
        pass

    @Cog.listener()
    async def on_bulk_message_delete(self, messages: t.List[Message]) -> None:
        # TODO: Ignore clean commands

        # We could upload these messages, but bulk deletion often includes big amounts
        # of messages, and uploading these might take a long time, it's probably not worth it
        embed = Embed(
            title="Bulk Message deletion",
            description=textwrap.dedent(
                f"""
                **Message Amount:** {len(messages)}
                [First message jump link]({messages[0].jump_url})
                [Last message jump link]({messages[-1].jump_url})
                """
            ),
            color=Color.dark_orange()
        )
        embed.timestamp = datetime.datetime.utcnow()

        await self.send_log(messages[0].guild, embed=embed)
        # TODO: Add these messages to ignored, for on_raw_bulk_message_deletes

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        # TODO: Finish this
        pass


def setup(bot: Bot) -> None:
    bot.add_cog(MessageLog(bot))

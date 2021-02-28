import asyncio
import datetime
import textwrap
import typing as t

from discord import Color, Embed, Guild, Message
from discord.errors import NotFound
from discord.ext.commands import Cog
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent

from bot.config import Event
from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.utils.paste_upload import upload_files, upload_text
from bot.utils.time import time_elapsed

# We should limit the maximum message size allowed for
# the embeds, to avoid huge embeds cluttering the message log
# for no reason, if they are over this size, we upload these
# messages to a paste service instead.
MAX_LOGGED_MESSAGE_SIZE = 800


class MessageLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self._handled_cached = set()

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
        # Add this message to set of ignored messages for raw events, these trigger even if
        # the message was cached, and to prevent double logging, we need to ignore them
        self._handled_cached.add((after.guild.id, after.id))

        if self.is_ignored(message=after, event=Event.message_edit):
            return

        response = (
            f"**Author:** {after.author.mention}\n"
            f"**Channel:** {after.channel.mention}"
        )
        if before.edited_at:
            response += f"\n**Last edited:** {time_elapsed(before.edited_at, after.edited_at, max_units=3)}"
        else:
            response += f"\n**Initially created:** {time_elapsed(before.created_at, after.edited_at, max_units=3)}"

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
        embed.timestamp = after.edited_at
        embed.set_footer(text=f"Message ID: {after.id}")

        await self.send_log(after.guild, embed=embed)

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent) -> None:
        """
        Send an embed whenever uncached message got edited, we do not have the
        previous contents of this message, so we can only send the current (edited)
        content, and the fact that it was actually edited.

        This listener trigers whenever a message is edited, this includes the messages
        that are cached and trigger `on_message_edit` directly, which means we have to
        ignore these.

        Disocrd's API also triggers this listener whenever an embed is sent. This is quite
        unexpected behavior for this event, and we should ignore it as it isn't an actual
        message edit event.

        In case neither of these cases are true, we may log the embed (with some further
        checks which are also present in `on_message_edit`, such as DM check).
        """
        # Try to fetch the message before it may get removed, if we don't manage that
        # we can ignore this event
        try:
            channel = self.bot.get_channel(int(payload.channel_id))
            message = await channel.fetch_message(payload.message_id)
        except NotFound:
            return

        # As described in docstring, this even also triggers on embed sending, if that's
        # the case, we can simply ignore that
        if "embeds" in payload.data and len(payload.data["embeds"]) > 0:
            return

        # Sleep for a while to leave enough time for normal event to execute, which will add this
        # channel into the handled cached set, to avoid double logging
        await asyncio.sleep(1)
        if (message.guild.id, message.id) in self._handled_cached:
            return

        if self.is_ignored(message, Event.message_edit):
            return

        response = (
            f"**Author:** {message.author.mention}\n"
            f"**Channel:** {message.channel.mention}\n"
            f"**Before:** This message is an uncached message, content can't be displayed"
        )

        if len(message.clean_content) > MAX_LOGGED_MESSAGE_SIZE:
            url = await upload_text(
                self.bot.http_session, message.content,
                file_name="message.md", paste_name="Automatic message upload.",
                paste_description="This paste was automatically generated from edited discrod message."
            )
            if url:
                response += f"\n**After:** Message too long, check [message upload]({url})"
            else:
                response += "\n**After:** Message too long (WARNING: Automatic upload failed"
        else:
            response += f"\n**After:** {message.content}"

        response += f"\n[Jump url]({message.jump_url})"

        embed = Embed(
            title="Uncached message edited",
            description=response,
            color=Color.dark_orange()
        )
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text=f"Message ID: {message.id}\n")

        await self.send_log(message.guild, embed=embed)

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
        # Add this message to set of ignored messages for raw events, these trigger even if
        # the message was cached, and to prevent double logging, we need to ignore them
        self._handled_cached.add((message.guild.id, message.id))

        if self.is_ignored(message, Event.message_delete):
            return

        # Add message to ignore list, to prevent raw event on executing
        self.bot.log_ignore(Event.message_delete, (message.guild.id, message.id))

        response = (
            f"**Author:** {message.author.mention}\n"
            f"**Channel:** {message.channel.mention}\n"
            f"**Initially created: ** {time_elapsed(message.created_at, max_units=3)}"
        )

        if message.attachments:
            readable_attachments = ', '.join(attachment.filename for attachment in message.attachments)
            response += f"\n**Attachment file-name{'s' if len(message.attachments) > 1 else ''}:** {readable_attachments}"

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
        embed.set_footer(text=f"Message ID: {message.id}")

        await self.send_log(message.guild, embed=embed)

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        """
        Send an embed whenever uncached message got deleted, we do not have the
        previous contents of this message, so we can only send the the fact that
        it was actually deleted, and channel it happened in.

        This listener trigers whenever a message is deleted, this includes the messages
        that are cached and trigger `on_message_delete` directly, which means we have to
        ignore these.

        In case this wasn't the case, we may log the embed (with some further
        checks which are also present in `on_message_edit`, such as DM check).
        """
        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        # Sleep for a while to leave enough time for normal event to execute, which will add this
        # channel into the handled cached set, to avoid double logging
        await asyncio.sleep(1)
        if (payload.guild_id, payload.message_id) in self._handled_cached:
            return

        if self.bot.log_is_ignored(Event.message_delete, (guild.id, payload.message_id)):
            return

        channel = self.bot.get_channel(payload.channel_id)
        embed = Embed(
            title="Uncached message deleted",
            description=textwrap.dedent(
                f"""
                **Channel:** {channel.mention if channel else 'Unable to get channel'}
                **Content:** This message is an uncached message, content can't be displayed
                """
            ),
            color=Color.dark_orange()
        )
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text=f"Message ID: {payload.message_id}")

        await self.send_log(guild, embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(MessageLog(bot))

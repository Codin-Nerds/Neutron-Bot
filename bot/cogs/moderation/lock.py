import asyncio
import typing as t
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from discord import TextChannel
from discord.ext.commands import Cog, Context, MissingPermissions, command
from loguru import logger

from bot.core.bot import Bot
from bot.core.converters import Duration
from bot.core.timer import Timer
from bot.database.permissions import Permissions
from bot.database.roles import Roles
from bot.utils.time import stringify_reldelta


class Lock(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.locked_channels = defaultdict(set)
        self.timer = Timer("channel_lock")
        self.roles_db: Roles = Roles.reference()
        self.permissions_db: Permissions = Permissions.reference()

    async def _lock(self, channel: TextChannel) -> bool:
        """
        Disable the permission to `send_messages`
        in `channel` for the `default_role` on that server.

        Return `False` in case the channel was already silenced,
        otherwise return `True`
        """
        default_role_id = self.roles_db.get_default_role(channel.guild)
        default_role = channel.guild.get_role(default_role_id)
        current_permissions = channel.overwrites_for(default_role)

        if current_permissions.send_messages is False:
            logger.warning(f"Tried to silence already silenced channel #{channel} ({channel.id}).")
            return False

        await channel.set_permissions(default_role, **dict(current_permissions, send_messages=False))
        self.locked_channels[channel.guild].add(channel)
        return True

    async def _unlock(self, channel: TextChannel) -> bool:
        """
        Reset the permission to `send_messages`
        in `channel` for the `default_role` on that server.
        """
        default_role_id = self.roles_db.get_default_role(channel.guild)
        default_role = channel.guild.get_role(default_role_id)
        current_permissions = channel.overwrites_for(default_role)

        if current_permissions.send_messages is not False:
            logger.warning(f"Tried to unsilence already unsilenced channel #{channel} ({channel.id}).")
            return False

        await channel.set_permissions(default_role, **dict(current_permissions, send_messages=None))
        self.locked_channels[channel.guild].discard(channel)
        return True

    @command(aliases=["silence"])
    async def lock(self, ctx: Context = None, duration: t.Optional[Duration] = None, *, reason: t.Optional[str]) -> None:
        """
        Disallow everyones permission to talk in this channel
        for given `duration` or indefinitely.
        """
        max_duration = await self.permissions_db.get_locktime(ctx.guild, ctx.author)

        if any([
            not duration and max_duration is not None,
            duration and max_duration is not None and duration > max_duration
        ]):
            raise MissingPermissions(["sufficient_locktime"])

        logger.debug(f"Channel #{ctx.channel} was silenced by {ctx.author}.")

        if not await self._lock(ctx.channel):
            await ctx.send(":x: This channel is already locked.")
            return

        reason = "No reason specified" if not reason else reason

        if not duration:
            await ctx.send(f"🔒 Channel locked indefinitely: {reason}.")
            return

        await ctx.send(f"🔒 Channel locked for {stringify_reldelta(relativedelta(seconds=duration))}: {reason}.")
        self.timer.delay(duration, ctx.channel.id, ctx.invoke(self.unlock))

    @command(aliases=["unsilence"])
    async def unlock(self, ctx: Context) -> None:
        """Unsilence current channel."""
        logger.debug(f"Channel #{ctx.channel} was unsilenced.")

        if await self._unlock(ctx.channel):
            self.timer.abort(ctx.channel.id)
            await ctx.send("🔓 Channel unlocked.")
        else:
            await ctx.send(":x: This channel isn't silenced.")

    def cog_unload(self) -> None:
        """Send a modlog message about the channels which were left unsilenced"""
        self.timer.abort_all()
        for guild, channels in self.locked_channels.items():
            moderator_role_id = self.roles_db.get_staff_role(guild.id)
            if moderator_role_id:
                message = f"<@&{moderator_role_id}> "
            else:
                message = ""
            message += "This channel was left locked after lock cog unloaded"
            for channel in channels:
                asyncio.create_task(channel.send(message))

    async def cog_check(self, ctx: Context) -> bool:
        """
        Only allow users with manage messages permission to use these function.

        Also make sure there's a default role set for that server.
        In case there isn't, send an error message.
        """
        if ctx.author.permissions_in(ctx.channel).manage_messages:
            return True

        return False


def setup(bot: Bot) -> None:
    bot.add_cog(Lock(bot))

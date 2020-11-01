import asyncio
import typing as t
from collections import defaultdict

from discord import TextChannel
from discord.ext.commands import Cog, Context, MissingPermissions, command
from loguru import logger

from bot.core.bot import Bot
from bot.core.converters import Duration
from bot.core.timer import Timer
from bot.database.permissions import Permissions
from bot.database.roles import Roles
from bot.utils.time import stringify_duration


class Lock(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.previous_permissions = defaultdict(lambda: defaultdict(None))
        self.timer = Timer("channel_lock")
        self.roles_db: Roles = Roles.reference()
        self.permissions_db: Permissions = Permissions.reference()

    async def _lock(self, channel: TextChannel) -> t.Literal[-1, 0, 1]:
        """
        Disable the permission to `send_messages`
        in `channel` for the `default_role` on that server.

        Return codes:
        - 1: Channel locked successfully
        - 0: Channel was already silenced
        - -1: Channel was silenced manually
        """
        default_role_id = self.roles_db.get_default_role(channel.guild)
        default_role = channel.guild.get_role(default_role_id)
        current_permissions = channel.overwrites_for(default_role)
        last_permissions = self.previous_permissions[channel.guild].get(channel)

        if last_permissions and current_permissions.send_messages is False:
            logger.warning(f"Tried to silence already silenced channel #{channel} ({channel.id}).")
            return 0

        elif current_permissions.send_messages is False:
            logger.warning(f"Tried to silence manually silenced channel #{channel} ({channel.id}).")
            return -1

        self.previous_permissions[channel.guild][channel] = current_permissions
        await channel.set_permissions(default_role, **dict(current_permissions, send_messages=False))

        return 1

    async def _unlock(self, channel: TextChannel) -> t.Literal[-2, -1, 0, 1]:
        """
        Reset the permission to `send_messages`
        in `channel` for the `default_role` on that server.

        Return codes:
        1: Channel successfully unlocked
        0: Channel wasn't silenced
        -1: Channel was already unsilenced manually
        -2: Channel was silenced manually
        """
        default_role_id = self.roles_db.get_default_role(channel.guild)
        default_role = channel.guild.get_role(default_role_id)
        current_permissions = channel.overwrites_for(default_role)
        last_permissions = self.previous_permissions[channel.guild].get(channel)

        if last_permissions and current_permissions.send_messages is not False:
            logger.warning(f"Tried to unsilence already manually unsilenced channel #{channel} ({channel.id}).")
            del self.previous_permissions[channel.guild][channel]
            return -1

        elif current_permissions.send_messages is not False:
            logger.warning(f"Tried to unsilence non-silenced channel #{channel} ({channel.id}).")
            return 0

        elif last_permissions is None:
            logger.warning(f"Tried to unsilence manually silenced channel #{channel} ({channel.id}).")
            return -2

        await channel.set_permissions(default_role, **dict(last_permissions))
        del self.previous_permissions[channel.guild][channel]

        return 1

    @command(aliases=["silence"])
    async def lock(self, ctx: Context, duration: t.Optional[Duration] = None, *, reason: t.Optional[str]) -> None:
        """
        Disallow everyones permission to talk in this channel
        for given `duration` or indefinitely.
        """
        if duration is None:
            duration = float("inf")

        max_duration = await self.permissions_db.get_locktime(ctx.guild, ctx.author)
        if max_duration != -1 and duration > max_duration:
            raise MissingPermissions(["sufficient_locktime"])

        logger.debug(f"Channel #{ctx.channel} was silenced by {ctx.author}.")

        status = await self._lock(ctx.channel)
        if status == 0:
            await ctx.send(":x: This channel is already locked.")
            return
        elif status == -1:
            await ctx.send(":x: This channel was already locked manually using channel permissions.")
            return

        reason = "No reason specified" if not reason else reason

        if duration == float("inf"):
            await ctx.send(f"🔒 Channel locked indefinitely: {reason}.")
            return

        await ctx.send(f"🔒 Channel locked for {stringify_duration(duration)}: {reason}.")
        self.timer.delay(duration, ctx.channel.id, ctx.invoke(self.unlock))

    @command(aliases=["unsilence"])
    async def unlock(self, ctx: Context) -> None:
        """Unsilence current channel."""
        logger.debug(f"Channel #{ctx.channel} was unsilenced.")

        status = await self._unlock(ctx.channel)
        if status == 1:
            self.timer.abort(ctx.channel.id)
            await ctx.send("🔓 Channel unlocked.")
        elif status == 0:
            await ctx.send(":x: This channel isn't locked.")
        elif status == -1:
            self.timer.abort(ctx.channel.id)
            await ctx.send(":x: This channel was already unsilenced manually, no action taken.")
        elif status == -2:
            await ctx.send(":x: This channel is silenced manually using channel permissions, you'll need to unsilence it manually.")

    def cog_unload(self) -> None:
        """Send a modlog message about the channels which were left unsilenced"""
        self.timer.abort_all()

        for guild, channels in self.previous_permissions.items():
            moderator_role_id = self.roles_db.get_staff_role(guild.id)
            if moderator_role_id:
                message = f"⚠️ <@&{moderator_role_id}> "
            else:
                message = "⚠️ "
            message += "This channel was left locked after lock cog unloaded, performing automatic unlock."

            for channel in channels.keys():
                logger.debug(f"Channel #{channel} ({channel.id}) was left locked after lock cog unloaded, performing automatic unlock.")
                asyncio.create_task(channel.send(message))
                asyncio.create_task(self._unlock(channel))

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

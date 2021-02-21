import datetime
import textwrap
import typing as t
from collections import defaultdict

from discord import AuditLogEntry, Color, Embed, Guild, Member, User
from discord.enums import AuditLogAction
from discord.errors import Forbidden
from discord.ext.commands import Cog

from bot.config import Event
from bot.core.bot import Bot
from bot.database.log_channels import LogChannels


class ModLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.ignored = defaultdict(set)  # usage described in `ignore` function
        self.kick_last = defaultdict(datetime.datetime.utcnow)  # usage described in `_identify_kick` function

    async def send_log(self, guild: Guild, *send_args, **send_kwargs) -> bool:
        """
        Try to send a log message to a mod_log channel for given guild,
        args and kwargs to this function will be used in the actual `Channel.send` call.

        If the message was sent, return True, otherwise return False
        (might happen if mod_log channel isn't defined in database).
        """
        mod_log_id = await LogChannels.get_log_channel(self.bot.db_session, "server_log", guild)
        mod_log_channel = guild.get_channel(mod_log_id)
        if mod_log_channel is None:
            return False

        await mod_log_channel.send(*send_args, **send_kwargs)
        return True

    def ignore(self, event: Event, *items: t.Any) -> None:
        """
        Add event to the set of ignored events to abort log sending.

        This function is meant for other cogs, to use and add ignored events,
        which is useful, because if we trigger an action like banning with a command,
        we may have more information about that ban, than we would get from the listener.
        The cog that ignored some event can then send a log message directly, with this
        additional info.
        """
        for item in items:
            if item not in self.ignored[event]:
                self.ignored[event].add(item)

    @Cog.listener()
    async def on_member_ban(self, guild: Guild, user: t.Union[User, Member]) -> None:
        if (guild.id, user.id) in self.ignored[Event.member_ban]:
            return

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, user: Member) -> None:
        if (guild.id, user.id) in self.ignored[Event.member_unban]:
            return

    @Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        """
        This is a handler which checks if there is a kick entry in audit log,
        when the member leaves, if there is, this wasn't a normal leave, but
        rather a moderator kick.
        """
        try:
            kick_log_entry = await self._identify_kick(member)
        except Forbidden:
            embed = Embed(
                title="Error parsing audit log",
                description="Parsing audit log for kick actions failed, "
                            "make sure to give the bot right to read audit log.",
                color=Color.red()
            )
            embed.timestamp = datetime.datetime.utcnow()
            await self.send_log(member.guild, ember=embed)
            return
        if kick_log_entry is None:
            return

        embed = Embed(
            title="User kicked",
            description=textwrap.dedent(
                f"""
                User: {member.mention}
                Author: {kick_log_entry.user.mention}
                Reason: {kick_log_entry.reason}
                """
            ),
            color=Color.dark_blue()
        )
        embed.timestamp = kick_log_entry.created_at
        await self.send_log(member.guild, embed=embed)

    async def _identify_kick(self, member: Member) -> t.Optional[AuditLogEntry]:
        """
        Kicking doesn't have a built listener, which means we have to rely on the
        member_remove listener, and identify, if given removal was a kick by checking
        the audit log entries.

        If a kick was found, `AuditLogEntry` of that kick is returned, otherwise, we return `None`
        """
        audit_logs = await member.guild.audit_logs(limit=1, action=AuditLogAction.kick).flatten()
        try:
            last_log = audit_logs[0]
        except IndexError:
            # No kick entry found in audit log
            return

        if last_log.target != member:
            # This kick was pointed at a different member
            return

        # Make sure to only go through audit logs within 5 seconds,
        # if this log is older, ignore it
        time_after = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
        if last_log.created_at < time_after:
            return

        # It is possible that the user will rejoin and leave after kick
        # within the given time limit (checked for above), we keep a cached
        # times for each user with the last audit log kick entry time, if
        # this cached version contains the time of this audit log entry, this
        # was the case and this isn't a valid kick, just a member leaving
        if last_log.created_at == self.kick_last[member]:
            return
        # if this wasn't the case, the kick is valid, and we should update the cache
        # with the new processed kick time
        self.kick_last[member] = last_log.created_at
        return last_log

    # TODO: Finish ban and unban listeners
    # TODO: Check for member role updates for muted role
    # TODO: Consider moving `ignore` function to `bot` class, for other cogs


def setup(bot: Bot) -> None:
    bot.add_cog(ModLog(bot))

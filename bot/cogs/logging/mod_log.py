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
from bot.database.roles import Roles


class ModLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.ignored = defaultdict(set)  # usage described in `ignore`
        self.audit_last = defaultdict(lambda: defaultdict(lambda: None))  # usage described in `_retreive_audit_action`

    async def send_log(self, guild: Guild, *send_args, **send_kwargs) -> bool:
        """
        Try to send a log message to a mod_log channel for given guild,
        args and kwargs to this function will be used in the actual `Channel.send` call.

        If the message was sent, return True, otherwise return False
        (might happen if mod_log channel isn't defined in database).
        """
        mod_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "server_log", guild)
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
        if (guild.id, user.id) in self.ignored[Event.member_unban]:
            return

        unban_log_entry = await self._retreive_audit_action(guild, AuditLogAction.ban, target=user)
        if unban_log_entry is None:
            return

        embed = Embed(
            title="User banned",
            description=textwrap.dedent(
                f"""
                User: {user.mention}
                Author: {unban_log_entry.user.mention}
                Reason: {unban_log_entry.reason}
                """
            ),
            color=Color.dark_orange()
        )
        embed.set_thumbnail(url=user.avatar_url)
        embed.timestamp = unban_log_entry.created_at
        await self.send_log(guild, embed=embed)

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, user: Member) -> None:
        if (guild.id, user.id) in self.ignored[Event.member_unban]:
            return

        ban_log_entry = await self._retreive_audit_action(guild, AuditLogAction.unban, target=user)
        if ban_log_entry is None:
            return

        embed = Embed(
            title="User unbanned",
            description=textwrap.dedent(
                f"""
                User: {user.mention}
                Author: {ban_log_entry.user.mention}
                Reason: {ban_log_entry.reason}
                """
            ),
            color=Color.dark_orange(),
        )
        embed.set_thumbnail(url=user.avatar_url)
        embed.timestamp = ban_log_entry.created_at
        await self.send_log(guild, embed=embed)

    @Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        """
        This is a handler which checks if there is a kick entry in audit log,
        when the member leaves, if there is, this wasn't a normal leave, but
        rather a kick. In which case, kick log is sent.
        """
        if (member.guild.id, member.id) in self.ignored[Event.member_kick]:
            return

        kick_log_entry = await self._retreive_audit_action(
            member.guild, AuditLogAction.kick,
            target=member, allow_repeating=False
        )
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
            color=Color.dark_orange()
        )
        embed.set_thumbnail(url=member.avatar_url)
        embed.timestamp = kick_log_entry.created_at
        await self.send_log(member.guild, embed=embed)

    @Cog.listener()
    async def on_member_update(self, member_before: Member, member_after: Member) -> None:
        """
        This is a handler which checks if muted role was added to given member,
        if it was, a log message is sent, describing this mute action.
        """
        if (member_after.guild.id, member_after.id) in self.ignored[Event.member_mute]:
            return

        if member_before.roles == member_after.roles:
            # Only continue if there was a role update. This listener does capture
            # more things, but we aren't interested in them here.
            return

        old_roles = set(member_before.roles)
        new_roles = set(member_after.roles)

        # These will always only contain 1 role, but we have
        # to use sets to meaningfully get it, which returns another set
        removed_roles = old_roles - new_roles
        added_roles = new_roles - old_roles

        muted_role_id = await Roles.get_role(self.bot.db_engine, "muted", member_after.guild)
        muted_role = member_after.guild.get_role(muted_role_id)
        if muted_role is None:
            return

        if muted_role not in added_roles.union(removed_roles):
            # Don't proceed if muted role wasn't added or removed
            return

        # TODO: Add mute strike

        description = f"User: {member_after.mention}"

        audit_entry = await self._retreive_audit_action(member_after.guild, AuditLogAction.member_role_update, target=member_before)
        if audit_entry is not None:
            description += f"\nAuthor: {audit_entry.user.mention}\nReason: {audit_entry.reason}"

        embed = Embed(
            title=f"User {'unmuted' if muted_role in removed_roles else 'muted'}",
            description=description,
            color=Color.dark_orange()
        )
        embed.set_thumbnail(url=member_after.avatar_url)
        embed.timestamp = audit_entry.created_at if audit_entry is not None else datetime.datetime.now()

        await self.send_log(member_after.guild, embed=embed)

    async def _retreive_audit_action(
        self,
        guild: Guild,
        action: AuditLogAction,
        target: t.Any = None,
        max_time: int = 5,
        allow_repeating: bool = True,
    ) -> t.Optional[AuditLogEntry]:
        """
        Many listeners often doesn't contain all the things which we could need
        to construct a meaningful and descriptive log message. Audit entries
        can help with this, because they contain useful information, such as
        responsible moderator for given action, action reason, etc.

        This function can be used, to obtain last audit entry for given `action`
        with given `target` (for example banned user) in given `max_time` (in seconds).

        There are some actions for which we don't want to be able to parse the same entry
        of the audit log twice, even though it would still be within the `max_time` limit.
        For that reason, there is `allow_repeating` keyword argument, which will block these.

        If an entry was found, `AuditLogEntry` is returned, otherwise, we return `None`.
        If bot doesn't have permission to access audit log, error embed is sent to
        mod_log channel, and `None` is returned
        """
        audit_logs = await guild.audit_logs(limit=1, action=action).flatten()
        try:
            last_log = audit_logs[0]
        except IndexError:
            # No such entry found in audit log
            return
        except Forbidden:
            # Bot can't access audit logs
            embed = Embed(
                title="Error parsing audit log",
                description="Parsing audit log for kick actions failed, "
                            "make sure to give the bot right to read audit log.",
                color=Color.red()
            )
            embed.timestamp = datetime.datetime.utcnow()
            await self.send_log(guild, ember=embed)
            return

        # Make sure to only go through audit logs within 5 seconds,
        # if this log is older, ignore it
        time_after = datetime.datetime.utcnow() - datetime.timedelta(seconds=max_time)
        if last_log.created_at < time_after:
            return

        if target is not None and last_log.target != target:
            # This entry was pointed at a different target
            return

        if allow_repeating is False:
            # Sometimes, we might not want to retreive the same audit log entry twice,
            # for example this is the case with kicks, if we already found an audit entry
            # for a valid kick, user rejoined and left on his own, within our `max_time`,
            # we would mark that leaving as a kick action, because we will scan the same
            # audit log entry twice, to prevent this, we keep a cache of times audit
            # log entries were created, and if they match, they're the same entry
            if last_log.created_at == self.audit_last[action][target]:
                return
            # if this wasn't the case, the entry is valid, and we should update the cache
            # with the new processed entry time
            self.audit_last[action][target] = last_log.created_at

        return last_log

    # TODO: Consider moving `ignore` function to `bot` class, for other cogs


def setup(bot: Bot) -> None:
    bot.add_cog(ModLog(bot))

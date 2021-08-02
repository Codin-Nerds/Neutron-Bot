import datetime
import typing as t

from discord import AuditLogEntry, Color, Embed, Guild
from discord.enums import AuditLogAction
from discord.errors import Forbidden


async def last_audit_log(
    guild: Guild,
    actions: t.Iterable[AuditLogAction],
    target: t.Any = None,
    max_time: int = 5,
    audit_cache: t.Optional[t.Set[AuditLogEntry]] = None,
) -> t.Optional[AuditLogEntry]:
    """
    This function can be used, to obtain last audit entry for given `actions`
    with given `target` (for example banned user) in given `max_time` (in seconds).

    Many listeners often doesn't contain all the things which we could need
    to construct a meaningful and descriptive log message. Audit entries
    can help with this, because they contain useful information, such as
    responsible moderator for given action, action reason, etc.

    In case `audit_cache` is provided, we will use it to check, if given audit entry
    was already checked. This is useful because there are certain things, where we don't
    want to parse the same entry of the audit log twice, even though it would match the
    search parameters.

    If an entry was found, `AuditLogEntry` is returned, otherwise, we return `None`.
    If bot doesn't have permission to access audit log, `Forbidden` exception is raised.
    """
    found_logs = []
    for action in actions:
        try:
            audit_logs = await guild.audit_logs(limit=1, action=action).flatten()
            found_logs.extend(audit_logs)
        except Forbidden as exc:  # Bot can't access audit logs
            raise exc

    # We haven't found any valid logs
    if len(found_logs) == 0:
        return

    # Get latest log from extracted ones
    last_log: AuditLogEntry = max(found_logs, key=lambda log_entry: log_entry.created_at)

    # Make sure to only go through audit logs within 5 seconds,
    # if this log is older, ignore it
    time_after = datetime.datetime.utcnow() - datetime.timedelta(seconds=max_time)
    if last_log.created_at < time_after:
        return

    # This entry was pointed at a different target
    if target is not None and last_log.target != target:
        return

    # Sometimes, we might not want to retreive the same audit log entry twice,
    # for example in the case with kicks, if we already found an audit entry
    # for a valid kick, user rejoined and left on his own, within our `max_time`,
    # we would mark that leaving as a kick action, because we will scan the same
    # audit log entry twice, to prevent this, we keep a cache of times audit
    # log entries were created, and if they match, they're the same entry
    if audit_cache is not None:
        if last_log not in audit_cache:
            return

        # if this wasn't the case, the entry is valid, and we should update the cache
        # with the new processed entry time
        audit_cache.add(last_log)

    return last_log


async def last_audit_log_with_fail_embed(
    guild: Guild,
    actions: t.Iterable[AuditLogAction],
    send_callback: t.Awaitable,
    target: t.Any = None,
    max_time: int = 5,
    audit_cache: t.Set[AuditLogEntry] = None,
) -> t.Optional[AuditLogEntry]:
    """
    This functions extends functionality of `last_audit_log` from `bot.utils.audit_parse`.

    We often need to send a failing message whenever parsing audit log fails, this function takes
    care of this, with accepting `send_callback` argument, that will be called with `embed` kwarg,
    to send this failing embed. Once this happens, we return `None`, instead of raising exception.
    """
    try:
        last_log = await last_audit_log(guild, actions, target, max_time, audit_cache)
    except Forbidden:
        embed = Embed(
            title="Error parsing audit log",
            description="Parsing audit log for kick actions failed, "
            "make sure to give the bot right to read audit log.",
            color=Color.red()
        )
        embed.timestamp = datetime.datetime.utcnow()
        await send_callback(embed=embed)
        return

    return last_log

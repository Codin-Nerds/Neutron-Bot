import datetime
import textwrap
import typing as t
from functools import partial

from discord import Color, Embed, Guild, Member, User
from discord.enums import AuditLogAction
from discord.ext.commands import Cog

from bot.config import Event
from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.database.roles import Roles
from bot.utils.audit_parse import last_audit_log_with_fail_embed, make_audit_cache


class ModLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.audit_cache = make_audit_cache()

    async def send_log(self, guild: Guild, *send_args, **send_kwargs) -> bool:
        """
        Try to send a log message to a mod_log channel for given guild,
        args and kwargs to this function will be used in the actual `Channel.send` call.

        If the message was sent, return True, otherwise return False
        (might happen if mod_log channel isn't defined in database).
        """
        mod_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "mod_log", guild)
        mod_log_channel = guild.get_channel(int(mod_log_id))
        if mod_log_channel is None:
            return False

        await mod_log_channel.send(*send_args, **send_kwargs)
        return True

    @Cog.listener()
    async def on_member_ban(self, guild: Guild, user: t.Union[User, Member]) -> None:
        if self.bot.log_is_ignored(Event.member_ban, (guild.id, user.id)):
            return

        unban_log_entry = await last_audit_log_with_fail_embed(
            guild,
            actions=[AuditLogAction.ban],
            send_callback=partial(self.send_log, guild),
            target=user
        )
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
            color=Color.dark_red()
        )
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=f"User ID: {user.id}")
        embed.timestamp = unban_log_entry.created_at

        await self.send_log(guild, embed=embed)

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, user: Member) -> None:
        if self.bot.log_is_ignored(Event.member_unban, (guild.id, user.id)):
            return

        ban_log_entry = await last_audit_log_with_fail_embed(
            guild,
            actions=[AuditLogAction.unban],
            send_callback=partial(self.send_log, guild),
            target=user
        )
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
            color=Color.dark_green(),
        )
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=f"User ID: {user.id}")
        embed.timestamp = ban_log_entry.created_at

        await self.send_log(guild, embed=embed)

    @Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        """
        This is a handler which checks if there is a kick entry in audit log,
        when the member leaves, if there is, this wasn't a normal leave, but
        rather a kick. In which case, kick log is sent.
        """
        if self.bot.log_is_ignored(Event.member_kick, (member.guild.id, member.id)):
            return

        kick_log_entry = await last_audit_log_with_fail_embed(
            member.guild,
            actions=[AuditLogAction.kick],
            send_callback=partial(self.send_log, member.guild),
            target=member,
            audit_cache=self.audit_cache
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
            color=Color.red()
        )
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f"User ID: {member.id}")
        embed.timestamp = kick_log_entry.created_at

        await self.send_log(member.guild, embed=embed)

    @Cog.listener()
    async def on_member_update(self, member_before: Member, member_after: Member) -> None:
        """
        This is a handler which checks if muted role was added to given member,
        if it was, a log message is sent, describing this mute action.
        """
        if self.bot.log_is_ignored(Event.member_mute, (member_after.guild.id, member_after.id)):
            return

        # Only continue if there was a role update. This listener does capture
        # more things, but we aren't interested in them here.
        if member_before.roles == member_after.roles:
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

        # Don't proceed if muted role wasn't added or removed
        if muted_role not in added_roles.union(removed_roles):
            return

        # TODO: Add mute strike

        description = f"User: {member_after.mention}"

        audit_entry = await last_audit_log_with_fail_embed(
            member_after.guild,
            actions=[AuditLogAction.member_role_update],
            send_callback=partial(self.send_log, member_after.guild),
            target=member_before
        )
        if audit_entry is not None:
            description += f"\nAuthor: {audit_entry.user.mention}\nReason: {audit_entry.reason}"

        embed = Embed(
            title=f"User {'unmuted' if muted_role in removed_roles else 'muted'}",
            description=description,
            color=Color.orange()
        )
        embed.set_thumbnail(url=member_after.avatar_url)
        embed.set_footer(text=f"User ID: {member_after.id}")
        embed.timestamp = audit_entry.created_at if audit_entry is not None else datetime.datetime.now()

        await self.send_log(member_after.guild, embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(ModLog(bot))

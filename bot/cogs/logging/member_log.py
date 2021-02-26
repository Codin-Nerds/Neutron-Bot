import datetime
import textwrap
import typing as t

from discord import Color, Embed, Guild, Member, User
from discord.channel import TextChannel
from discord.ext.commands import Cog

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels


class MemberLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_log(self, guild: Guild) -> t.Optional[TextChannel]:
        """
        Try to obtain the proper channel for given guild, if the channel is
        found, return it, otherwise, return `None`.
        """
        member_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "member_log", guild)
        return guild.get_channel(int(member_log_id))

    async def send_log(self, guild: Guild, *send_args, **send_kwargs) -> bool:
        """
        Try to send a log message to a member_log channel for given guild,
        args and kwargs to this function will be used in the actual `Channel.send` call.

        If the message was sent, return True, otherwise return False
        (might happen if member_log channel isn't defined in database).
        """
        member_log_channel = await self.get_log(guild)

        if member_log_channel is None:
            return False

        await member_log_channel.send(*send_args, **send_kwargs)
        return True

    @Cog.listener()
    async def on_member_update(self, member_before: Member, member_after: Member) -> None:
        if member_before.status != member_after.status or member_before.activity != member_after.activity:
            # Don't track changes of statuses and activities, they happen very often
            # and it would mean spamming member_log too much, it is usually
            # not worth tracking anyway.
            return
        elif member_before.nick != member_after.nick:
            embed = Embed(
                title="Nickname change",
                description=textwrap.dedent(
                    f"""
                    **Mention:** {member_after.mention}
                    **Previous:** {member_before.nick}
                    **Current:** {member_after.nick}
                    """
                ),
                color=Color.blue()
            )
        elif member_before.roles != member_after.roles:
            # TODO: Consider looking into audit logs to find who did this
            old_roles = set(member_before.roles)
            new_roles = set(member_after.roles)

            # These will always only contain 1 role, but we have
            # to use sets to meaningfully get it, which returns another set
            removed_roles = old_roles - new_roles
            added_roles = new_roles - old_roles

            if removed_roles:
                embed = Embed(
                    title="Role removed",
                    description=textwrap.dedent(
                        f"""
                        **Role:** {removed_roles.pop().mention}
                        **Mention:** {member_after.mention}
                        """
                    ),
                    color=Color.blue()
                )
            else:
                embed = Embed(
                    title="Role added",
                    description=textwrap.dedent(
                        f"""
                        **Role:** {added_roles.pop().mention}
                        **Mention:** {member_after.mention}
                        """
                    ),
                    color=Color.blue()
                )
        elif member_before.pending != member_after.pending:
            embed = Embed(
                title="User verified",
                description=textwrap.dedent(
                    f"""
                    User has agreed to membership screening rules.
                    **Mention:** {member_after.mention}
                    """
                ),
                color=Color.blue()
            )
        else:
            # member_update ran without any changes
            # this usually happens because on_user_update takes over
            return

        embed.set_thumbnail(url=member_after.avatar_url)
        embed.timestamp = datetime.datetime.utcnow()

        await self.send_log(member_after.guild, embed=embed)

    @Cog.listener()
    async def on_user_update(self, user_before: User, user_after: User) -> None:
        if user_before.avatar != user_after.avatar:
            embed = Embed(
                title="Avatar change",
                description=textwrap.dedent(
                    f"""
                    **Previous:** [link]({user_before.avatar_url})
                    **Current:** [link]({user_after.avatar_url})
                    **Mention:** {user_after.mention}
                    """
                ),
                color=Color.blue()
            )
        elif user_before.name != user_after.name:
            embed = Embed(
                title="Username change",
                description=textwrap.dedent(
                    f"""
                    **Previous:** {user_before.name}
                    **Current:** {user_after.name}
                    **Mention:** {user_after.mention}
                    """
                ),
                color=Color.blue()
            )
        elif user_before.discriminator != user_after.discriminator:
            embed = Embed(
                title="Discriminator change",
                description=textwrap.dedent(
                    f"""
                    **Previous:** {user_before.discriminator}
                    **Current:** {user_after.discriminator}
                    **Mention:** {user_after.mention}
                    """
                ),
                color=Color.blue()
            )
        else:
            return

        embed.set_thumbnail(url=user_after.avatar_url)
        embed.timestamp = datetime.datetime.utcnow()

        member_log_channels = []
        for guild in self.bot.guilds:
            if guild.get_member(user_after.id) is None:
                continue

            member_log_channel = self.get_log(guild)
            if member_log_channel:
                member_log_channels.append(member_log_channel)

        for member_log_channel in member_log_channels:
            await member_log_channel.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(MemberLog(bot))

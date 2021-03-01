import datetime
import textwrap

from discord import Color, Embed, Guild, Member
from discord.ext.commands import Cog

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.utils.converters import Ordinal
from bot.utils.time import time_elapsed


class JoinLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_log(self, guild: Guild, *send_args, **send_kwargs) -> bool:
        """
        Try to send a log message to a join_log channel for given guild,
        args and kwargs to this function will be used in the actual `Channel.send` call.

        If the message was sent, return True, otherwise return False
        (might happen if join_log channel isn't defined in database).
        """
        join_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "join_log", guild)
        join_log_channel = guild.get_channel(int(join_log_id))
        if join_log_channel is None:
            return False

        await join_log_channel.send(*send_args, **send_kwargs)
        return True

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        embed = Embed(
            title="Member joined",
            description=textwrap.dedent(
                f"""
                **Mention:** {member.mention}
                **Created:** {time_elapsed(member.created_at, max_units=3)}
                **Members:** They are {Ordinal.make_ordinal(member.guild.member_count)} to join.
                """
            ),
            color=Color.green(),
        )
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f"Member ID: {member.id}")

        await self.send_log(member.guild, embed=embed)

    @Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        roles = ", ".join(role.mention for role in member.roles[1:])
        embed = Embed(
            title="Member left",
            description=textwrap.dedent(
                f"""
                **Mention:** {member.mention}
                **Joined:** {time_elapsed(member.joined_at, max_units=3)}
                **Roles:** {roles if roles else None}
                **Members:** Server is now at {member.guild.member_count} members.
                """
            ),
            color=Color.dark_orange(),
        )
        embed.timestamp = datetime.datetime.now()
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f"Member ID: {member.id}")

        await self.send_log(member.guild, embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(JoinLog(bot))

import datetime
import textwrap

from discord import Color, Embed, Member
from discord.ext.commands import Cog

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.utils.converters import Ordinal
from bot.utils.time import time_elapsed


class JoinLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        join_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "join_log", member.guild)
        join_log_channel = member.guild.get_channel(join_log_id)
        if join_log_channel is None:
            return

        embed = Embed(
            title="Member joined",
            description=textwrap.dedent(
                f"""
                **Mention:** {member.mention}
                **Created:** {time_elapsed(member.created_at, max_units=3)}
                **ID:** {member.id}
                He is {Ordinal.make_ordinal(member.guild.member_count)} to join.
                """
            ),
            color=Color.green(),
        )
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_thumbnail(url=member.avatar_url)
        await join_log_channel.send(embed=embed)

    @Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        join_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "join_log", member.guild)
        join_log_channel = member.guild.get_channel(join_log_id)
        if join_log_channel is None:
            return

        roles = ", ".join(role.mention for role in member.roles[1:])
        embed = Embed(
            title="Member left",
            description=textwrap.dedent(
                f"""
                **Mention:** {member.mention}
                **Joined:** {time_elapsed(member.joined_at, max_units=3)}
                **Roles:** {roles if roles else None}
                **ID:** {member.id}
                Server is now at {member.guild.member_count} members.
                """
            ),
            color=Color.dark_orange(),
        )
        embed.timestamp = datetime.datetime.now()
        embed.set_thumbnail(url=member.avatar_url)
        await join_log_channel.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(JoinLog(bot))

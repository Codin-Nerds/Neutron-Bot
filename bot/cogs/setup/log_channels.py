import textwrap
import typing as t

from discord import Embed
from discord.ext.commands import Cog, Context, TextChannelConverter, group
from discord.ext.commands.errors import MissingPermissions

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels


class LogChannelsSetup(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @group(invoke_without_command=True, aliases=["logging", "log", "logs", "logchannel"])
    async def logging_group(self, ctx: Context) -> None:
        """Commands for configuring the log channels."""
        await ctx.send_help(ctx.command)

    @logging_group.command(aliases=["serverlog", "server"])
    async def server_log(self, ctx: Context, channel: TextChannelConverter) -> None:
        """Set the channel for server level logs."""
        await LogChannels.set_log_channel(self.bot.db_session, "server", ctx.guild, channel)
        await ctx.send(":white_check_mark: Log channel updated.")

    @logging_group.command(aliases=["modlog", "mod"])
    async def mod_log(self, ctx: Context, channel: TextChannelConverter) -> None:
        """Set the channel for moderator level logs."""
        await LogChannels.set_log_channel(self.bot.db_session, "mod", ctx.guild, channel)
        await ctx.send(":white_check_mark: Log channel updated.")

    @logging_group.command(aliases=["messagelog", "message"])
    async def message_log(self, ctx: Context, channel: TextChannelConverter) -> None:
        """Set the channel for message level logs."""
        await LogChannels.set_log_channel(self.bot.db_session, "message", ctx.guild, channel)
        await ctx.send(":white_check_mark: Log channel updated.")

    @logging_group.command(aliases=["memberlog", "member"])
    async def member_log(self, ctx: Context, channel: TextChannelConverter) -> None:
        """Set the channel for member level logs."""
        await LogChannels.set_log_channel(self.bot.db_session, "member", ctx.guild, channel)
        await ctx.send(":white_check_mark: Log channel updated.")

    @logging_group.command(aliases=["joinlog", "join"])
    async def join_log(self, ctx: Context, channel: TextChannelConverter) -> None:
        """Set the channel for join level logs."""
        await LogChannels.set_log_channel(self.bot.db_session, "join", ctx.guild, channel)
        await ctx.send(":white_check_mark: Log channel updated.")

    @logging_group.command(aliases=["info", "status"])
    async def show(self, ctx: Context) -> None:
        """Show configured log channels."""
        log_channels = await LogChannels.get_log_channels(self.bot.db_session, ctx.guild)

        server_log = ctx.guild.get_channel(log_channels["server_log"]) if log_channels["server_log"] else None
        mod_log = ctx.guild.get_channel(log_channels["mod_log"]) if log_channels["mod_log"] else None
        message_log = ctx.guild.get_channel(log_channels["message_log"]) if log_channels["message_log"] else None
        member_log = ctx.guild.get_channel(log_channels["member_log"]) if log_channels["member_log"] else None
        join_log = ctx.guild.get_channel(log_channels["join_log"]) if log_channels["join_log"] else None

        embed = Embed(
            description=textwrap.dedent(
                f"""
                **Log channels configuration:**

                Server level logs: {server_log.mention if server_log else "<Undefined>"}
                Moderator level logs: {mod_log.mention if mod_log else "<Undefined>"}
                Message level logs: {message_log.mention if message_log else "<Undefined>"}
                Member level logs: {member_log.mention if member_log else "<Undefined>"}
                Join level logs: {join_log.mention if join_log else "<Undefined>"}
                """
            )
        )

        await ctx.send(embed=embed)

    async def cog_check(self, ctx: Context) -> t.Optional[bool]:
        """Only allow users with administrator permission to use these functions."""
        if ctx.author.guild_permissions.administrator:
            return True

        raise MissingPermissions("Only members with administrator rights can use this command.")


def setup(bot: Bot) -> None:
    bot.add_cog(LogChannelsSetup(bot))

import typing as t

from discord import Color, Embed
from discord.ext.commands import Cog, Context, TextChannelConverter, group
from discord.ext.commands.errors import MissingPermissions

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels


class LogChannelsSetup(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @group(invoke_without_command=True, aliases=["logging", "log", "logs", "logchannel"])
    async def logging_group(self, ctx: Context, log_type: str, channel: TextChannelConverter) -> None:
        """Commands for configuring the log channels."""
        try:
            await LogChannels.set_log_channel(self.bot.db_engine, log_type, ctx.guild, channel)
        except ValueError:
            await ctx.send(f":x: Invalid logging type, types: `{', '.join(LogChannels.valid_log_types)}`")
            return
        await ctx.send(":white_check_mark: Log channel updated")

    @logging_group.command(aliases=["info", "status"])
    async def show(self, ctx: Context) -> None:
        """Show configured log channels."""
        obtained_channels = await LogChannels.get_log_channels(self.bot.db_engine, ctx.guild)

        description_lines = []
        for log_type in LogChannels.valid_log_types:
            channel_id = obtained_channels.get(log_type, None)
            channel = ctx.guild.get_channel(channel_id)

            readable_log_type = log_type.replace("_log", "").capitalize()
            description_lines.append(f"{readable_log_type} level logs: {channel.mention if channel else '<not configured>'}")

        embed = Embed(
            title="Log channels configuration",
            description="\n".join(description_lines),
            color=Color.blue()
        )

        await ctx.send(embed=embed)

    async def cog_check(self, ctx: Context) -> t.Optional[bool]:
        """Only allow users with administrator permission to use these functions."""
        if ctx.author.guild_permissions.administrator:
            return True

        raise MissingPermissions("Only members with administrator rights can use this command.")


def setup(bot: Bot) -> None:
    bot.add_cog(LogChannelsSetup(bot))

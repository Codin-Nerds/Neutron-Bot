from discord.ext.commands import BadArgument, Cog, Context, command
from loguru import logger

from bot.core.bot import Bot
from bot.core.converters import Duration
from bot.utils.time import stringify_duration


class Slowmode(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @command(aliases=["slowmode"])
    async def slow_mode(self, ctx: Context, duration: Duration) -> None:
        """
        Apply slow mode on channel the command was invoked from.

        Maximum duration for slowmode is 6 hours (discords limitation)
        Using 0 for duration will turn off the slowmode
        """
        if duration > 6 * 60 * 60:  # maximum of 6 hours
            raise BadArgument("Maximum duration is 6 hours")

        await ctx.channel.edit(slowmode_delay=duration)

        if duration:
            log_msg = f"ser {ctx.author} applied slowmode to #{ctx.channel} for {stringify_duration(duration)}"
            msg = f"⏱️ Applied slowmode for this channel, time delay: {stringify_duration(duration)}."
        else:
            log_msg = f"User {ctx.author} removed slowmode from #{ctx.channel}"
            msg = "💬 Slowmode removed."

        logger.debug(log_msg)
        await ctx.send(msg)

    async def cog_check(self, ctx: Context) -> bool:
        """
        Only allow users with manage messages permission to use these function.

        Also make sure there's a default role set for that server.
        In case there isn't, send an error message.
        """
        if ctx.author.permissions_in(ctx.channel).manage_channels:
            return True

        return False


def setup(bot: Bot) -> None:
    bot.add_cog(Slowmode(bot))

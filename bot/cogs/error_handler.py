import typing as t

from discord import Color, Embed
from discord.ext.commands import Cog, Context, errors
from loguru import logger

from bot.core.bot import Bot


class ErrorHandler(Cog):
    """This cog handles the errors invoked from commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_error_embed(self, ctx: Context, title: t.Optional[str], description: t.Optional[str]) -> None:
        embed = Embed(
            title=title,
            description=description,
            color=Color.red()
        )
        await ctx.send(embed=embed)

    @Cog.listener()
    async def on_command_error(self, ctx: Context, exception: errors.CommandError) -> None:
        logger.debug(
            f"Exception {exception.__class__.__name__}: {exception} has occurred in "
            f" command {ctx.command} invoked by {ctx.author.id} on {ctx.guild.id}"
        )


def setup(bot: Bot) -> None:
    bot.add_cog(ErrorHandler(bot))

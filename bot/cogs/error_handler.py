import textwrap
import typing as t

from discord import Color, Embed
from discord.ext.commands import Cog, Context, errors
from loguru import logger

from bot.core.bot import Bot


class ErrorHandler(Cog):
    """This cog handles the errors invoked from commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def _send_error_embed(self, ctx: Context, title: t.Optional[str], description: t.Optional[str]) -> None:
        embed = Embed(
            title=title,
            description=description,
            color=Color.red()
        )
        await ctx.send(embed=embed)

    async def send_unhandled_embed(self, ctx: Context, exception: errors.CommandError) -> None:
        logger.debug(
            f"Exception {exception.__class__.__name__}: {exception} has occurred from "
            f"message {ctx.message.content} invoked by {ctx.author.id} on {ctx.guild.id}"
        )
        await self._send_error_embed(
            ctx,
            title="Unhandled exception",
            description=textwrap.dedent(
                f"""
                Unknown error has occurred without being properly handled.
                Please report this at the [bot repository](https://github.com/Codin-Nerds/Neutron-Bot/issues)

                Exception details:
                ```
                {exception.__class__.__name__}: {exception}
                ```
                """
            )
        )

    @Cog.listener()
    async def on_command_error(self, ctx: Context, exception: errors.CommandError) -> None:
        """
        Handle exceptions which occurred while running some command.

        The error handle order is as follows:
        1. `UserInputError`: references `handle_user_input_error`
        2. `CommandNotFound`: references `handle_command_not_found`
        3. `CheckFailure`: references `handle_command_not_found`
        4. Otherwise, send unhandled error embed with `send_unhandled_embed`
        """
        if isinstance(exception, errors.UserInputError):
            await self.handle_user_input_error(ctx, exception)
            return
        elif isinstance(exception, errors.CommandNotFound):
            await self.handle_command_not_found(ctx, exception)
            return
        elif isinstance(exception, errors.CheckFailure):
            await self.handle_check_failure(ctx, exception)
            return

        await self.send_unhandled_embed(ctx, exception)

    async def handle_user_input_error(self, ctx: Context, exception: errors.UserInputError) -> None:
        pass

    async def handle_command_not_found(self, ctx: Context, exception: errors.CommandNotFound) -> None:
        pass

    async def handle_check_failure(self, ctx: Context, exception: errors.CheckFailure) -> None:
        pass


def setup(bot: Bot) -> None:
    bot.add_cog(ErrorHandler(bot))

import textwrap
import typing as t
from json import JSONDecodeError

from discord import Color, Embed
from discord.ext.commands import Cog, Context, errors
from loguru import logger

from bot.cogs.embeds import InvalidEmbed
from bot.core.bot import Bot


class ErrorHandler(Cog):
    """This cog handles the errors invoked from commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def _send_error_embed(self, ctx: Context, title: t.Optional[str] = None, description: t.Optional[str] = None) -> None:
        embed = Embed(
            title=title,
            description=description,
            color=Color.red()
        )
        await ctx.send(f"Sorry {ctx.author.mention}", embed=embed)

    async def send_unhandled_embed(self, ctx: Context, exception: errors.CommandError) -> None:
        logger.warning(
            f"Exception {exception.__repr__()} has occurred from "
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
                ```{exception.__class__.__name__}: {exception}```
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
        4. `CommandInvokeError`: this error is raised when any unknown exception
        was raised in a command, it references `send_unhandled_embed` with the specific
        exception which has occurred in the command in case it doesn't match the more
        specific filters.
        5. Otherwise, send unhandled error embed with `send_unhandled_embed`
        """
        if isinstance(exception, errors.UserInputError):
            await self.handle_user_input_error(ctx, exception)
            return
        elif isinstance(exception, errors.CommandNotFound):
            # Ignore command not found due to possibility of other bots with the
            # same command prefix
            return
        elif isinstance(exception, errors.CheckFailure):
            await self.handle_check_failure(ctx, exception)
            return
        elif isinstance(exception, errors.CommandInvokeError):
            original_exception = exception.__cause__
            if isinstance(original_exception, JSONDecodeError):
                await self.handle_json_decode_error(ctx, original_exception)
                return
            if isinstance(original_exception, InvalidEmbed):
                await self.handle_invalid_embed(ctx, original_exception)
                return

            await self.send_unhandled_embed(ctx, original_exception)
            # Raise the original exception to show the traceback
            raise original_exception
            return

        await self.send_unhandled_embed(ctx, exception)

    async def handle_user_input_error(self, ctx: Context, exception: errors.UserInputError) -> None:
        command = ctx.command
        parent = command.full_parent_name

        command_name = str(command) if not parent else f"{parent} {command.name}"
        command_syntax = f"```{command_name} {command.signature}```"

        aliases = [f"`{alias}`" if not parent else f"`{parent} {alias}`" for alias in command.aliases]
        aliases = ", ".join(sorted(aliases))

        command_help = f"*{command.help or 'No description provided.'}*"

        await self._send_error_embed(
            ctx,
            title="Invalid command syntax",
            description=textwrap.dedent(
                f"""
                Your command usage is incorrect: **{exception}**

                **Command syntax**
                {command_syntax}
                **Command Description**
                {command_help}

                {f"Aliases: {aliases}" if aliases else None}
                """
            )
        )

    async def handle_check_failure(self, ctx: Context, exception: errors.CheckFailure) -> None:
        await self._send_error_embed(
            ctx,
            description="❌ You don't have permission to run this command"
        )

    async def handle_json_decode_error(self, ctx: Context, exception: JSONDecodeError) -> None:
        msg = textwrap.dedent(
            f"""
            Sorry, I couldn't parse this JSON:
            ```
            {exception.msg}
            ```
            The error occurred on *`line {exception.lineno} column {exception.colno} (char {exception.pos})`*
            """
        )
        if exception.lines:
            msg += textwrap.dedent(
                f"""
                ```
                {exception.lines[exception.lineno - 1]}
                {" " * (int(exception.colno) - 1)}^
                ```
                """
            )

        await self._send_error_embed(ctx, description=msg)

    async def handle_invalid_embed(self, ctx: Context, exception: InvalidEmbed) -> None:
        msg = textwrap.dedent(
            f"""
            Your embed isn't valid:
            ```{exception.message}```

            Discord error code: `{exception.discord_code}`
            API Response: `{exception.status_code}: {exception.status_text}`
            """
        )

        await self._send_error_embed(
            ctx,
            description=msg
        )


def setup(bot: Bot) -> None:
    bot.add_cog(ErrorHandler(bot))

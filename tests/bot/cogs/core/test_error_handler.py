import unittest
import unittest.mock
from json.decoder import JSONDecodeError

from discord.ext.commands.errors import CheckFailure, UserInputError, CommandInvokeError

from bot.cogs.core.error_handler import ErrorHandler
from bot.cogs.utility.embeds import InvalidEmbed
from tests.dpy_mocks import MockBot, MockContext


class ErrorHandlerCogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bot = MockBot()
        self.cog = ErrorHandler(self.bot)
        self.context = MockContext()

        # Avoid problems with `ctx.command.aliases` not being iterable
        self.context.command.aliases = []

    async def test_send_error_embed(self):
        """Test that _send_error_embed does actually send an embed message."""
        await self.cog._send_error_embed(self.context, "title", "description")
        self.context.send.assert_awaited_once()

    async def test_send_unhandled_embed(self):
        """TRest that send_unhandled_embed calls lower level _send_error_embed function."""
        # Replace the actual _send_error_embed with an AsyncMock, so that we can make sure that
        # it was actually ran, also running the actual _send_error_embed function would be out
        # of scope for this specific test
        _send_error_embed = unittest.mock.AsyncMock()
        with unittest.mock.patch("bot.cogs.core.error_handler.ErrorHandler._send_error_embed", _send_error_embed):
            await self.cog.send_unhandled_embed(self.context, Exception())
            _send_error_embed.assert_awaited_once()

    async def test_proper_handler_used(self):
        """Make sure that on_command_errors uses the correct handlers for given exception types."""
        # Define some exception that would clutter the test_cases  here as simple variables
        exc_json_decode_error = CommandInvokeError(JSONDecodeError(msg="my message", doc="error line", pos=0))
        exc_json_decode_error.__cause__ = exc_json_decode_error.original

        exc_invalid_embed = CommandInvokeError(InvalidEmbed(
            discord_code=unittest.mock.Mock(),
            status_code=unittest.mock.Mock(),
            status_text=unittest.mock.Mock(),
            message=unittest.mock.Mock()
        ))
        exc_invalid_embed.__cause__ = exc_invalid_embed.original

        test_cases = (
            (UserInputError(), "handle_user_input_error"),
            (CheckFailure(), "handle_check_failure"),
            (exc_json_decode_error, "handle_json_decode_error"),
            (exc_invalid_embed, "handle_invalid_embed"),
            # This isn't actually an error handler, however there is no
            # error handler for unhandled exception, so we instead just
            # send the unhandled embed directly, for the purposes of this
            # test, this will work fine
            (RuntimeError(), "send_unhandled_embed"),
        )

        # Override the handler for given exception so that we can check whether a call was
        # made to it, it also prevents from running the actual handler functions, which isn't the
        # intention behind this test.
        mocked_handler = unittest.mock.AsyncMock()

        for exception, handler_function_name in test_cases:
            with unittest.mock.patch(f"bot.cogs.core.error_handler.ErrorHandler.{handler_function_name}", mocked_handler):
                with self.subTest(exception=exception, handler_function_name=handler_function_name):
                    await self.cog.on_command_error(self.context, exception)
                    mocked_handler.assert_awaited_once()
                    mocked_handler.reset_mock()

    async def test_error_handlers_send_embed(self):
        """Make sure that all error handlers send an embed."""
        # Define some exceptions that would clutter the test_cases here as simple variables
        exc_json_decode_error = JSONDecodeError(msg="my message", doc="error line", pos=0)
        exc_json_decode_error.lines = unittest.mock.MagicMock()
        exc_invalid_embed = InvalidEmbed(
            discord_code=unittest.mock.Mock(),
            status_code=unittest.mock.Mock(),
            status_text=unittest.mock.Mock(),
            message=unittest.mock.Mock()
        )

        test_cases = (
            ("handle_user_input_error", self.cog.handle_user_input_error, UserInputError()),
            ("handle_check_failure", self.cog.handle_check_failure, CheckFailure()),
            ("handle_json_decode_error", self.cog.handle_json_decode_error, exc_json_decode_error),
            ("handle_invalid_embed", self.cog.handle_invalid_embed, exc_invalid_embed),
        )

        # Override the _send_error_embed async function so that we can test whether a call was made to it,
        # it also prevents from running this function, since that's not the intention behind this test
        _send_error_embed = unittest.mock.AsyncMock()

        with unittest.mock.patch("bot.cogs.core.error_handler.ErrorHandler._send_error_embed", _send_error_embed):
            for handler_name, handler_function, exception in test_cases:
                with self.subTest(msg=f"Make sure {handler_name} sends an embed."):
                    await handler_function(self.context, exception)
                    _send_error_embed.assert_awaited_once()
                    _send_error_embed.reset_mock()

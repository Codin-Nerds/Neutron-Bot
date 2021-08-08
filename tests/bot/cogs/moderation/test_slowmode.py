import unittest

from discord.ext.commands.errors import BadArgument

from bot.cogs.moderation.slowmode import Slowmode
from tests.dpy_mocks import MockBot, MockContext, MockTextChannel


class SlowmodeCogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bot = MockBot()
        self.cog = Slowmode(self.bot)
        self.context = MockContext()
        self.text_channel = MockTextChannel(name="my-channel", slowmode_delay=1)
        self.context.channel = self.text_channel

    async def test_slowmode_changes_time_delay(self):
        """Make sure that when the slow_mode command is ran properly, """
        new_time = 10  # seconds
        await self.cog.slow_mode(self.cog, self.context, new_time)
        self.assertEqual(self.text_channel.slowmode_delay, new_time)

    async def test_slowmode_sends_message(self):
        """Ensure that slow_mode command sends the expected message to the affected channel."""
        new_time = 10  # seconds
        await self.cog.slow_mode(self.cog, self.context, new_time)
        self.context.send.assert_called_once_with(f"⏱️ Applied slowmode for this channel, time delay: {new_time} seconds.")

    async def test_slowmode_invalid_duration(self):
        """Discord only supports slowmode duration of up to 6 hours, make sure we respect that."""
        new_time = 6 * 60 * 60 + 1  # 6 hours (in seconds) + 1
        with self.assertRaises(BadArgument):
            await self.cog.slow_mode(self.cog, self.context, new_time)

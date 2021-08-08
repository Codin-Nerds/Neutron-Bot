import unittest

from discord import Permissions
from discord.ext.commands.errors import BadArgument, MissingPermissions

from bot.cogs.moderation.slowmode import Slowmode
from tests.dpy_mocks import MockBot, MockContext, MockMember, MockTextChannel


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

    async def test_cog_check(self):
        """Only members with manage_messages permissions should be allowed to use this cog."""
        authorized_member = MockMember()
        authorized_member.permissions_in.return_value = Permissions(manage_channels=True)
        unauthorized_member = MockMember()
        unauthorized_member.permissions_in.return_value = Permissions(manage_channels=False)

        with self.subTest(test_member=authorized_member, msg="Test cog_check on authorized member"):
            self.context.author = authorized_member
            result = await self.cog.cog_check(self.context)
            self.assertEqual(result, True)

        with self.subTest(test_member=unauthorized_member, msg="Test cog_check on unauthorized member"):
            self.context.author = unauthorized_member
            with self.assertRaises(MissingPermissions):
                await self.cog.cog_check(self.context)

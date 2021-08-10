import unittest

from discord.ext.commands.errors import NotOwner

from bot.cogs.core.sudo import Sudo
from tests.dpy_mocks import MockBot, MockContext


class SudoCogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bot = MockBot()
        self.cog = Sudo(self.bot)
        self.context = MockContext()

    async def test_cog_check(self):
        """Only members with manage_messages permissions should be allowed to use this cog."""

        with self.subTest(msg="Test cog_check on bot owner"):
            self.bot.is_owner.return_value = True
            result = await self.cog.cog_check(self.context)
            self.assertEqual(result, True)

        with self.subTest(msg="Test cog_check on non bot owner"):
            self.bot.is_owner.return_value = False
            with self.assertRaises(NotOwner):
                await self.cog.cog_check(self.context)

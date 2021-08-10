import unittest
import unittest.mock

from discord import Permissions
from discord.ext.commands.errors import MissingPermissions

from bot.cogs.moderation.strikes import Strikes
from bot.config import StrikeType
from tests.dpy_mocks import MockBot, MockContext, MockMember, MockUser


class StrikesCogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bot = MockBot()
        self.cog = Strikes(self.bot)
        self.context = MockContext()

    async def test_add(self):
        """Test add strike command."""
        mocked_strikes_db = unittest.mock.AsyncMock()
        with unittest.mock.patch("bot.cogs.moderation.strikes.StrikesDB", mocked_strikes_db):
            await self.cog.add(self.cog, self.context, MockUser(), StrikeType.kick)
            mocked_strikes_db.set_strike.assert_awaited_once()

    async def test_remove(self):
        """Test add strike command."""
        mocked_strikes_db = unittest.mock.AsyncMock()
        with unittest.mock.patch("bot.cogs.moderation.strikes.StrikesDB", mocked_strikes_db):
            await self.cog.remove(self.cog, self.context, 1)
            mocked_strikes_db.remove_strike.assert_awaited_once()

    async def test_cog_check(self):
        """Only members with administrator permissions should be allowed to use this cog."""
        authorized_member = MockMember()
        authorized_member.permissions_in.return_value = Permissions(administrator=True)
        unauthorized_member = MockMember()
        unauthorized_member.permissions_in.return_value = Permissions(administrator=False)

        with self.subTest(test_member=authorized_member, msg="Test cog_check on authorized member"):
            self.context.author = authorized_member
            result = await self.cog.cog_check(self.context)
            self.assertEqual(result, True)

        with self.subTest(test_member=unauthorized_member, msg="Test cog_check on unauthorized member"):
            self.context.author = unauthorized_member
            with self.assertRaises(MissingPermissions):
                await self.cog.cog_check(self.context)

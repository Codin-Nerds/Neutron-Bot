import unittest

from discord import Permissions

from bot.cogs.automod.filepaste import FilePaste
from tests.dpy_mocks import MockAttachment, MockBot, MockMember, MockMessage, MockUser


async def fake_upload_attachments(*a, **kw) -> str:
    """
    Fake upload_attachments function that's being called by the on_message event handler.
    We don't want to run the real function because that would try to upload the content
    of our mocked attachment to paste.gg which isn't what we're testing here.

    Simply return `http://example.com` as the URL no matter the input parameters.
    """
    return "https://example.com"


class FilePasteCogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bot = MockBot()
        self.cog = FilePaste(self.bot)

    @unittest.mock.patch("bot.cogs.automod.filepaste.upload_attachments", fake_upload_attachments)
    async def test_in_dm(self):
        """Test that a user in a DM can send any message without it being removed."""
        dm_user = MockUser()
        disallowed_attachment = MockAttachment(filename="file_with_disallowed_extension.exe")
        message = MockMessage(author=dm_user, attachments=[disallowed_attachment])
        await self.cog.on_message(message)

    @unittest.mock.patch("bot.cogs.automod.filepaste.upload_attachments", fake_upload_attachments)
    async def test_regular_member_no_attachments(self):
        """Test that a member without manage_messages permissions can post a message without any attachments."""
        regular_member = MockMember()
        regular_member.permissions_in.return_value = Permissions(manage_messages=False)
        message = MockMessage(author=regular_member, attachments=[])
        await self.cog.on_message(message)

        message.delete.assert_not_awaited()

    @unittest.mock.patch("bot.cogs.automod.filepaste.upload_attachments", fake_upload_attachments)
    async def test_regular_member_allowed_extension(self):
        """Test that a member without manage_messages permissions can post an attachments with allowed extension."""
        regular_member = MockMember()
        regular_member.permissions_in.return_value = Permissions(manage_messages=False)
        allowed_attachment = MockAttachment(filename="file_with_disallowed_extension.png")
        message = MockMessage(author=regular_member, attachments=[allowed_attachment])
        await self.cog.on_message(message)

        message.delete.assert_not_awaited()

    @unittest.mock.patch("bot.utils.paste_upload.upload_attachments", fake_upload_attachments)
    async def test_excepted_member_disallowed_extension(self):
        """Test that a member with manage_messages permissions is excepted from posting disallowed attachments."""
        excepted_member = MockMember()
        excepted_member.permissions_in.return_value = Permissions(manage_messages=True)
        disallowed_attachment = MockAttachment(filename="file_with_disallowed_extension.exe")
        message = MockMessage(author=excepted_member, attachments=[disallowed_attachment])
        await self.cog.on_message(message)

        message.delete.assert_not_awaited()

    @unittest.mock.patch("bot.cogs.automod.filepaste.upload_attachments", fake_upload_attachments)
    async def test_regular_member_disallowed_extension(self):
        """Test that a member without manage_messages permissions have the message removed when posting disallowed attachments."""
        regular_member = MockMember()
        regular_member.permissions_in.return_value = Permissions(manage_messages=False)
        disallowed_attachment = MockAttachment(filename="file_with_disallowed_extension.exe")
        message = MockMessage(author=regular_member, attachments=[disallowed_attachment])
        await self.cog.on_message(message)

        message.delete.assert_awaited_once()

    @unittest.mock.patch("bot.cogs.automod.filepaste.upload_attachments", fake_upload_attachments)
    async def test_regular_member_disallowed_extension_message(self):
        """Test that a member without manage_messages permissions will get an embed with the link to his uploaded attachments.."""
        regular_member = MockMember()
        regular_member.permissions_in.return_value = Permissions(manage_messages=False)
        disallowed_attachment = MockAttachment(filename="file_with_disallowed_extension.exe")
        message = MockMessage(author=regular_member, attachments=[disallowed_attachment])
        await self.cog.on_message(message)

        # Obtain the non-changing URL from fake_upload_attachments function
        fake_upload_url = await fake_upload_attachments()

        # Get the value for the auto-upload field within the sent embed
        embed = message.channel.send.await_args[1]["embed"]
        auto_update_field_value = embed.fields[0].value

        # Ensure that this field's value contained our upload_url
        self.assertIn(fake_upload_url, auto_update_field_value)

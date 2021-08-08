# This file holds mocked discord.py structures, which will be used within
# tests to provide a way of passing these mocked objects.
import datetime
import itertools
import typing as t
import unittest.mock

import discord
import discord.ext.commands
from aiohttp import ClientSession
from sqlalchemy.ext.asyncio import AsyncEngine

from bot.__main__ import bot as bot_instance


# Discord objects often require `state` argument, this can be a simple `MagicMock`.
mock_state = unittest.mock.MagicMock()


class CustomMockMixin:
    """
    This class is here to provide common functionality for our mock classes.

    We usually don't want to propagate the same custom mock class for newly
    accessed attributes of given class, but rather make new independent mocks,
    generally our objects won't have attributes that hold instances of that
    same class, so it doesn't make sense to propagate them like this here.

    It provides `spec_asyncs_extend` parameter that allows us to easily
    extend the `_spec_asyncs` and the accessed attributes will be returning
    `AsyncMock` instances instead of just `Mock` instances.

    The class also provides `discord_id` generator, that will produce a unique
    incremental discord id for each mocked discord instance, to avoid collisions.
    """
    spec_set = None
    spec_asyncs_extend = None
    discord_id = itertools.count(0)

    def __init__(self, **kwargs):
        super().__init__(spec_set=self.spec_set, **kwargs)

        # Add custom attributes that should be given AsyncMocks in addition
        # to the methods added by default from the unittest.mock implementation.
        if self.spec_asyncs_extend:
            self._spec_asyncs.extend(self.spec_asyncs_extend)

    def _get_child_mock(self, **kwargs):
        """
        By default, when we're accessing an attribute of a given mock, it will
        default to making another mocked instance of that same type (using that
        same custom mock class), we usually don't want this since our objects
        generally won't have attributes that hold instances of the parent's class.

        This method overrides the default implementation and generates instances
        of simple independent `unittest.mock.Mock` or `unittest.mock.AsyncMock`
        objects, rather than `self.__class__` objects.

        This approach also prevents RecursionErrors when defining some attribute
        of a mock, which would be making that attribute as an instance of the
        original class, that again tries to define this attribute.
        """
        new_name = kwargs.get("_new_name")

        # Check if the accessed attribute is defined in the spec list of async attributes
        if new_name in self._spec_asyncs:
            return unittest.mock.AsyncMock(**kwargs)

        # Mocks can be sealed, in which case we wouldn't want to allow propagation of any
        # kind and rather raise an AttributeError, informing that given attr isn't accessible
        if self._mock_sealed:
            mock_name = self._extract_mock_name()
            if "name" in kwargs:
                raise AttributeError(f"{mock_name}.{kwargs['name']}")
            else:
                raise AttributeError(f"{mock_name}()")

        # If we're using magic mocks, and we attempt to access one of the async
        # dunder methods (e.g.: __aenter__), automatically return AsyncMock
        if issubclass(type(self), unittest.mock.MagicMock):
            return unittest.mock.AsyncMock(**kwargs)

        # Propagate any other non-async children as simple `unittest.mock.Mock` instances
        # rather than `self.__class__` instances, which is the default behavior
        return unittest.mock.Mock(**kwargs)


class ColorMixin:
    """
    Discord often allows for accessing/setting both 'color' and 'colour' arguments that
    correspond to a single value, this class replicates this behavior with the use of
    properties, it can then be subclassed in a mock discord object class to apply it.
    """
    @property
    def color(self) -> discord.Colour:
        return self.colour

    @color.setter
    def color(self, color: discord.Colour) -> None:
        self.colour = color


guild_data = {
    "id": 734712951621025822,
    "name": "Codin' Nerds",
    "region": "Europe",
    "verification_level": 2,
    "default_notifications": 1,
    "afk_timeout": 100,
    "icon": "icon.png",
    "banner": "banner.png",
    "mfa_level": 1,
    "splash": "splash.png",
    "system_channel_id": 464033278631084042,
    "description": "test guild mock",
    "max_presences": 10_000,
    "max_members": 100_000,
    "preferred_locale": "UTC",
    "owner_id": 306876636526280705,
    "afk_channel_id": 464033278631084042,
}
guild_instance = discord.Guild(data=guild_data, state=mock_state)


class MockGuild(CustomMockMixin, unittest.mock.Mock):
    """A class for creating mocked `discord.Guild` objects."""
    spec_set = guild_instance

    def __init__(self, roles: t.Optional[t.Iterable["MockRole"]] = None, **kwargs):
        new_kwargs = {"id": next(self.discord_id), "members": []}
        new_kwargs.update(kwargs)

        # Handle `roles` separately, because we always need to add
        # a special `@everyone` role
        new_kwargs["roles"] = [MockRole(name="@everyone", position=1, id=0)]
        if roles:
            new_kwargs["roles"].extend(roles)

        super().__init__(**new_kwargs)


role_data = {"id": 734712951637934093, "name": "Admin"}
role_instance = discord.Role(guild=guild_instance, state=mock_state, data=role_data)


class MockRole(CustomMockMixin, unittest.mock.Mock, ColorMixin):
    """A class for creating mocked `discord.Role` objects."""
    spec_set = role_instance

    def __init__(self, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "name": "MockedRole",
            "position": 1,
            "colour": discord.Colour(0x000000),
            "permissions": discord.Permissions()
        }
        new_kwargs.update(kwargs)
        if "mention" not in new_kwargs:
            new_kwargs["mention"] = f"&{new_kwargs['name']}"

        super().__init__(**new_kwargs)

        # Replicate discord's way of passing color/permissions as pure int objects
        # and converting them to proper representative objects afterwards.
        if isinstance(self.colour, int):
            self.colour = discord.Colour(self.colour)
        if isinstance(self.permissions, int):
            self.permissions = discord.Permissions(self.permissions)

    def __lt__(self, other):
        """Position-based comparisons just like in `discord.Role`"""
        return self.position < other.position

    def __ge__(self, other):
        """Position-based comparisons just like in `discord.Role`"""
        return self.position >= other.position


member_data = {"user": "ItsDrike", "roles": [1]}
member_instance = discord.Member(data=member_data, guild=guild_instance, state=mock_state)


class MockMember(CustomMockMixin, unittest.mock.Mock, ColorMixin):
    """A class for creating mocked `discord.Member` objects."""
    spec_set = member_instance

    def __init__(self, roles: t.Optional[t.Iterable["MockRole"]] = None, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "name": "MockedMember",
            "pending": False,
            "bot": False
        }
        new_kwargs.update(kwargs)

        if "mention" not in new_kwargs:
            new_kwargs["mention"] = f"&{new_kwargs['name']}"

        # Handle `roles` separately, because we always need to add
        # a special `@everyone` role
        new_kwargs["roles"] = [MockRole(name="@everyone", position=1, id=0)]
        if roles:
            new_kwargs["roles"].extend(roles)

        super().__init__(**new_kwargs)


user_data = {
    "id": 306876636526280705,
    "username": "ItsDrike",
    "discriminator": 5359,
    "avatar": "avatar.png"
}
user_instance = discord.User(data=user_data, state=mock_state)


class MockUser(CustomMockMixin, unittest.mock.Mock, ColorMixin):
    """A class for creating mocked `discord.User` objects."""
    spec_set = user_instance

    def __init__(self, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "name": "MockUser",
            "bot": False
        }
        new_kwargs.update(kwargs)

        if "mention" not in new_kwargs:
            new_kwargs["mention"] = f"&{new_kwargs['name']}"
        super().__init__(**new_kwargs)


text_channel_data = {
    "id": 734712951872815138,
    "type": "TextChannel",
    "name": "global-chat",
    "parent_id": 734712951872815137,
    "topic": "Main discussion channel",
    "position": 1,
    "nsfw": False,
    "last_message_id": 1
}
text_channel_instance = discord.TextChannel(data=text_channel_data, guild=guild_instance, state=mock_state)


class MockTextChannel(CustomMockMixin, unittest.mock.Mock):
    """A class for creating mocked `discord.TextChannel` objects."""
    spec_set = text_channel_instance

    def __init__(self, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "name": "MockedTextChannel",
            "guild": MockGuild()
        }
        new_kwargs.update(kwargs)
        if "mention" not in new_kwargs:
            new_kwargs["mention"] = f"&{new_kwargs['name']}"

        super().__init__(**new_kwargs)

    async def edit(self, **kwargs) -> None:
        """
        Mimic the `discord.TextChannel.edit` method which makes a discord API call and
        changes certain attributes of a text channel to only change the attributes,
        without making the actual API calls.

        Note: This will fail if we attempt to edit a non-existent attributes, as this mock
        only supports attribute definitions for attributes that are also present in the
        spec_set model.
        """
        for arg, value in kwargs.items():
            setattr(self, arg, value)


voice_channel_data = {
    "id": 734712952342577192,
    "type": "VoiceChannel",
    "name": "General",
    "parent_id": 734712952115953743,
    "position": 1
}
voice_channel_instance = discord.VoiceChannel(data=voice_channel_data, guild=guild_instance, state=mock_state)


class MockVoiceChannel:
    """A class for creating mocked `discord.VoiceChannel` objects."""
    spec_set = voice_channel_instance

    def __init__(self, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "name": "MockedTextChannel",
            "guild": MockGuild()
        }
        new_kwargs.update(kwargs)
        if "mention" not in new_kwargs:
            new_kwargs["mention"] = f"&{new_kwargs['name']}"

        super().__init__(**new_kwargs)


category_channel_data = {
    "id": 734712951872815137,
    "name": "Social",
    "position": 1
}
category_channel_instance = discord.CategoryChannel(data=category_channel_data, guild=guild_instance, state=mock_state)


class MockCategoryChannel:
    """A class for creating mocked `discord.CategoryChannel` objects."""
    spec_set = category_channel_instance

    def __init__(self, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "name": "MockCategoryChannel",
            "guild": MockGuild()
        }
        new_kwargs.update(kwargs)
        super().__init__(**new_kwargs)


dm_channel_data = {"id": 1, "recipients": [user_instance]}
dm_channel_instance = discord.DMChannel(me=user_instance, data=dm_channel_data, state=mock_state)


class MockDMChannel:
    """A class for creating mocked `discord.DMChannel` objects."""
    spec_set = dm_channel_instance

    def __init__(self, **kwargs):
        new_kwargs = {"id": next(self.discord_id), "recipient": MockUser(), "me": MockUser(bot=True)}
        new_kwargs.update(kwargs)
        super().__init__(**new_kwargs)


message_data = {
    "id": 1,
    "attachments": [],
    "embeds": [],
    'edited_timestamp': datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat(timespec="seconds"),
    "type": "message",
    "pinned": False,
    "mention_everyone": False,
    "tts": False,
    "content": "I'm a message",
}
message_instance = discord.Message(data=message_data, channel=text_channel_instance, state=mock_state)


class MockMessage(CustomMockMixin, unittest.mock.Mock):
    """A class for creating mocked `discord.Message` objects."""
    spec_set = message_instance

    def __init__(self, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "attachments": [],
            "reactions": [],
            "embeds": [],
            "channel": MockTextChannel(),
            "pinned": False,
            "mention_everyone": False,
            "tts": False,
            "content": "MockMessage",
            "stickers": [],
            "author": MockMember(),
            "guild": MockGuild()
        }
        new_kwargs.update(kwargs)
        super().__init__(**new_kwargs)


attachment_data = {
    "id": 1,
    "size": 1000,
    "height": 100,
    "width": 300,
    "filename": "my_attachment.txt",
    "url": "https://www.example.com",
    "proxy_url": "https://www.example.com"
}
attachment_instance = discord.Attachment(data=attachment_data, state=mock_state)


class MockAttachment(CustomMockMixin, unittest.mock.Mock):
    """A class for creating mocked `discord.Attachment` objects."""
    spec_set = attachment_instance

    def __init__(self, **kwargs):
        new_kwargs = {"id": next(self.discord_id)}
        new_kwargs.update(kwargs)
        super().__init__(**new_kwargs)


emoji_data = {
    "id": 1,
    "require_colons": True,
    "managed": True,
    "name": "coding_nerds"
}
emoji_instance = discord.Emoji(data=emoji_data, guild=guild_instance, state=mock_state)


class MockEmoji(CustomMockMixin, unittest.mock.Mock):
    """A class for creating mocked `discord.Emoji` objects."""
    spec_set = emoji_instance

    def __init__(self, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "name": "MockEmoji",
            "guild": MockGuild(),
            "managed": True,
            "require_colons": True
        }
        new_kwargs.update(kwargs)
        super().__init__(**new_kwargs)


reaction_data = {"me": True}
reaction_instance = discord.Reaction(data=reaction_data, message=MockMessage(), emoji=MockEmoji())


class MockReaction(CustomMockMixin, unittest.mock.Mock):
    """A class for creating mocked `discord.Reaction` objects."""
    spec_set = reaction_instance

    def __init__(self, users: t.Optional[t.Iterable[MockUser]] = None, **kwargs):
        new_kwargs = {
            "emoji": MockEmoji(),
            "message": MockMessage(),
        }
        new_kwargs.update(kwargs)
        super().__init__(**new_kwargs)

        # Handle `users` separately, as they need a special __aiter__ AsyncMock
        if users is None:
            users = []

        user_iterator = unittest.mock.AsyncMock()
        user_iterator.__aiter__.return_value = users
        self.users.return_value = user_iterator

    def __str__(self):
        """Replicate the behavior of `discord.Reaction` and return str of `self.emoji`"""
        return str(self.emoji)


webhook_data = {
    "id": 1,
    "type": discord.WebhookType.incoming.value
}
webhook_instance = discord.Webhook(
    data=webhook_data,
    adapter=unittest.mock.create_autospec(spec=discord.AsyncWebhookAdapter, spec_set=True)
)


class MockWebhook(CustomMockMixin, unittest.mock.Mock):
    """A class for creating mocked `discord.Webhook` objects."""
    spec_set = webhook_instance
    spec_asyncs_extend = ("send", "edit", "delete", "execute")

    def __init__(self, **kwargs):
        new_kwargs = {
            "id": next(self.discord_id),
            "type": discord.WebhookType.incoming
        }
        # Resolve type int into discord.WebhookType enum
        if "type" in kwargs:
            kwargs["type"] = discord.enums.try_enum(discord.enums.WebhookType, int(kwargs["type"]))
        new_kwargs.update(kwargs)
        super().__init__(**new_kwargs)


context_instance = discord.ext.commands.Context(
    prefix=bot_instance.get_prefix(message_instance),
    message=message_instance
)


class MockContext(CustomMockMixin, unittest.mock.Mock):
    """A class for creating mocked `discord.ext.commands.Context` objects."""
    spec_set = context_instance

    def __init__(self, **kwargs):
        new_kwargs = {
            "bot": MockBot(),
            "guild": MockGuild(),
            "author": MockMember(),
            "channel": MockTextChannel(),
            "message": MockMessage()
        }
        new_kwargs.update(kwargs)
        super().__init__(**new_kwargs)


class MockBot(CustomMockMixin, unittest.mock.MagicMock):
    """A class for creating mocked `bot.core.bot.Bot` objects."""
    spec_set = bot_instance

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Replicate certain attributes that the bot needs
        self.http_session = unittest.mock.create_autospec(spec=ClientSession, spec_set=True)
        self.db_engine = unittest.mock.create_autospec(spec=AsyncEngine, spec_set=True)

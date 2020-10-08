import typing as t
from dataclasses import dataclass

from discord import Guild, TextChannel
from loguru import logger

from bot.core.bot import Bot
from bot.database import DBTable, Database


@dataclass
class Entry:
    """Class for storing the database rows of log_channels table."""
    server: int = 0
    mod: int = 0
    message: int = 0
    member: int = 0
    join: int = 0


class LogChannels(DBTable):
    """
    This table stores all guild-specific roles:
    * `server` log channel
    * `mod` log channel
    * `message` log channel
    * `member` log channel
    * `join` log channel
    Under the single `serverid` column
    """

    columns = {
        "serverid": "NUMERIC(40) UNIQUE NOT NULL",
        "server": "NUMERIC(40) DEFAULT 0",
        "mod": "NUMERIC(40) DEFAULT 0",
        "message": "NUMERIC(40) DEFAULT 0",
        "member": "NUMERIC(40) DEFAULT 0",
        "join": "NUMERIC(40) DEFAULT 0"
    }

    caching = {
        "key": (int, "serverid"),

        "server": (int, 0),
        "mod": (int, 0),
        "message": (int, 0),
        "member": (int, 0),
        "join": (int, 0)
    }

    def __init__(self, bot: Bot, database: Database):
        super().__init__(database, "log_channels")
        self.bot = bot
        self.database = database
        self.cache: t.Dict[int, Entry] = {}

    async def _set_channel(self, channel_name: str, guild: t.Union[Guild, int], channel: t.Union[TextChannel, int]) -> None:
        """Set a `channel_name` column to store `channel.id` for the specific `guild.id`."""
        if isinstance(channel, TextChannel):
            channel = channel.id
        if isinstance(guild, Guild):
            guild = guild.id

        logger.debug(f"Setting {channel_name}-log channel on {guild} to <#{channel}>")
        await self.db_upsert(
            columns=["serverid", channel_name],
            values=[guild, channel],
            conflict_columns=["serverid"]
        )
        self.update_cache(guild, channel_name, channel)

    def _get_channel(self, channel_name: str, guild: t.Union[Guild, int]) -> int:
        """Get a `role_name` column for specific `guild` from cache."""
        if isinstance(guild, Guild):
            guild = guild.id
        return self.cache_get(guild, channel_name)

    async def set_server_log(self, guild: t.Union[Guild, int], channel: t.Union[TextChannel, int]) -> None:
        await self._set_channel("server", guild, channel)

    async def set_mod_log(self, guild: t.Union[Guild, int], channel: t.Union[TextChannel, int]) -> None:
        await self._set_channel("mod", guild, channel)

    async def set_message_log(self, guild: t.Union[Guild, int], channel: t.Union[TextChannel, int]) -> None:
        await self._set_channel("message", guild, channel)

    async def set_member_log(self, guild: t.Union[Guild, int], channel: t.Union[TextChannel, int]) -> None:
        await self._set_channel("member", guild, channel)

    async def set_join_log(self, guild: t.Union[Guild, int], channel: t.Union[TextChannel, int]) -> None:
        await self._set_channel("join", guild, channel)

    def get_server_log(self, guild: t.Union[Guild, int]) -> int:
        return self._get_channel("server", guild)

    def get_mod_log(self, guild: t.Union[Guild, int]) -> int:
        return self._get_channel("mod", guild)

    def get_message_log(self, guild: t.Union[Guild, int]) -> int:
        return self._get_channel("message", guild)

    def get_member_log(self, guild: t.Union[Guild, int]) -> int:
        return self._get_channel("member", guild)

    def get_join_log(self, guild: t.Union[Guild, int]) -> int:
        return self._get_channel("join", guild)


async def load(bot: Bot, database: Database) -> None:
    await database.add_table(LogChannels(bot, database))

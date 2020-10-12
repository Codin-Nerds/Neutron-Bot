import typing as t
from dataclasses import dataclass

from discord import Guild, Role
from loguru import logger

from bot.core.bot import Bot
from bot.database import DBTable, Database


@dataclass
class Entry:
    """Class for storing the database rows of roles table."""
    _default: int
    muted: int
    staff: int


class Permissions(DBTable):
    """
    This table stores these permissions:
    * `bantime` maximum amount of time (in seconds) for temp-ban
    * `mutetime` maximum amount of time (in seconds) for temp-mute
    * `locktime` maximum amount of time (in seconds) for channel lock
    For given `role` in given `serverid`
    """
    columns = {
        "serverid": "NUMERIC(40) NOT NULL",
        "role": "NUMERIC(40) DEFAULT 0",
        "bantime": "INTEGER DEFAULT 0",
        "mutetime": "INTEGER DEFAULT 0",
        "locktime": "INTEGER DEFAULT 0",
        "UNIQUE": "(serverid, role)"
    }

    def __init__(self, bot: Bot, database: Database):
        super().__init__(database, "permissions")
        self.bot = bot
        self.database = database

    async def _set_permission(self, permission_name: str, guild: t.Union[Guild, int], role: t.Union[Role, int], value: t.Any) -> None:
        """Set a `role_name` column to store `role` for the specific `guild`."""
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(role, Role):
            role = role.id

        logger.debug(f"Setting {permission_name} on {guild} for <@&{role}> to {value}")
        await self.db_upsert(
            columns=["serverid", "role", permission_name],
            values=[guild, role, value],
            conflict_columns=["serverid", "role"]
        )

    async def _get_permission(self, permission_name: str, guild: t.Union[Guild, int], role: t.Union[Role, int]) -> t.Any:
        """Get a `role_name` column for specific `guild` from cache."""
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(role, Role):
            role = role.id

        record = await self.db_get(
            columns=[permission_name],
            specification="serverid=$1 AND role=$2",
            sql_args=[guild, role]
        )

        return record[0]

    async def set_bantime(self, guild: t.Union[Guild, int], role: t.Union[Role, int], value: int) -> None:
        await self._set_permission("bantime", guild, role, value)

    async def set_mutetime(self, guild: t.Union[Guild, int], role: t.Union[Role, int], value: int) -> None:
        await self._set_permission("mutetime", guild, role, value)

    async def set_locktime(self, guild: t.Union[Guild, int], role: t.Union[Role, int], value: int) -> None:
        await self._set_permission("locktime", guild, role, value)

    async def get_bantime(self, guild: t.Union[Guild, int], role: t.Union[Role, int]) -> int:
        return await self._get_permission("bantime", guild, role)

    async def get_mutetime(self, guild: t.Union[Guild, int], role: t.Union[Role, int]) -> int:
        return await self._get_permission("mutetime", guild, role)

    async def get_locktime(self, guild: t.Union[Guild, int], role: t.Union[Role, int]) -> int:
        return await self._get_permission("locktime", guild, role)


async def load(bot: Bot, database: Database) -> None:
    await database.add_table(Permissions(bot, database))

import typing as t
from dataclasses import dataclass
from textwrap import dedent

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


class Roles(DBTable):
    """
    This table stores all guild-specific roles:
    * `default` role (column is named `_default` to avoid SQL confusion)
    * `muted` role
    * `staff` role
    Under the single `serverid` column
    """
    populate_command = dedent("""
        CREATE TABLE IF NOT EXISTS roles (
            serverid NUMERIC(40) UNIQUE NOT NULL,
            _default NUMERIC(40) DEFAULT 0,
            muted NUMERIC(40) DEFAULT 0,
            staff NUMERIC(40) DEFAULT 0
        )
    """)

    def __init__(self, bot: Bot, database: Database):
        super().__init__(database, "roles")
        self.bot = bot
        self.database = database
        self.cache: t.Dict[int, Entry] = {}

    async def __async_init__(self):
        """
        Obtain all database rows and populate the cache
        with them.
        """
        entries = await self.db_get(columns=["serverid", "_default", "muted", "staff"])

        for entry in entries:
            lst_entry = list(entry)
            self.cache[lst_entry[0]] = Entry(*lst_entry[1:])

    def update_cache(self, server_id: int, role: str, value: int) -> None:
        """Update or add roles in stored cache."""
        if server_id in self.cache:
            setattr(self.cache[server_id], role, value)
        else:
            roles = {"_default": 0, "muted": 0, "staff": 0}
            roles.update({role: value})
            self.cache[server_id] = self.Entry(**roles)

    async def _set_role(self, role_name: str, guild: t.Union[Guild, int], role: t.Union[Role, int]) -> None:
        """Set a `role_name` column to store `role` for the specific `guild`."""
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(role, Role):
            role = role.id

        logger.debug(f"Setting {role_name} role on {guild} to <@&{role}>")
        await self.db_upsert(
            columns=["serverid", role_name],
            values=[guild, role],
            conflict_column="serverid"
        )
        self.update_cache(guild.id, role_name, role.id)

    def _get_role(self, role_name: str, guild: t.Union[Guild, int]) -> int:
        """Get a `role_name` column for specific `guild` from cache."""
        if isinstance(guild, Guild):
            guild = guild.id
        return getattr(self.cache[guild], role_name)

    async def set_default_role(self, guild: t.Union[Guild, int], role: t.Union[Role, int]) -> None:
        await self._set_role("_default", guild, role)

    async def set_muted_role(self, guild: t.Union[Guild, int], role: t.Union[Role, int]) -> None:
        await self._set_role("muted", guild, role)

    async def set_staff_role(self, guild: t.Union[Guild, int], role: t.Union[Role, int]) -> None:
        await self._set_role("staff", guild, role)

    def get_default_role(self, guild: t.Union[Guild, int]) -> int:
        role = self._get_role("_default", guild)
        if role == 0:
            role = guild.default_role

        return role

    def get_muted_role(self, guild: t.Union[Guild, int]) -> int:
        return self._get_role("muted", guild)

    def get_staff_role(self, guild: t.Union[Guild, int]) -> int:
        return self._get_role("staff", guild)


async def load(bot: Bot, database: Database) -> None:
    await database.add_table(Roles(bot, database))

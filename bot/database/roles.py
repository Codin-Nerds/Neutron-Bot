from textwrap import dedent

from discord import Guild, Role
from loguru import logger

from bot.core.bot import Bot
from bot.database import DBTable, Database


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

    async def _set_role(self, role_name: str, guild: Guild, role: Role) -> None:
        """Set a `role_name` column to store `role` for the specific `guild`."""
        logger.debug(f"Setting {role_name} role on {guild.id} to <@&{role.id}>")
        await self.db_upsert(
            columns=["serverid", role_name],
            values=[guild.id, role.id],
            conflict_column="serverid"
        )

    async def _get_role(self, role_name: str, guild: Guild) -> Role:
        """Get a `role_name` column for specific `guild`."""
        logger.trace(f"Obtaining {role_name} role from {guild.id}")
        record = await self.db_get(
            column=[role_name],
            specification="serverid=$1",
            sql_args=[guild.id]
        )
        role_id = int(list(record.values())[0])
        return guild.get_role(role_id)

    async def set_default_role(self, guild: Guild, role: Role) -> None:
        await self._set_role("_default", guild, role)

    async def set_muted_role(self, guild: Guild, role: Role) -> None:
        await self._set_role("muted", guild, role)

    async def set_staff_role(self, guild: Guild, role: Role) -> None:
        await self._set_role("staff", guild, role)

    async def get_default_role(self, guild: Guild) -> Role:
        return await self._get_role("_default", guild)

    async def get_muted_role(self, guild: Guild) -> Role:
        return await self._get_role("muted", guild)

    async def get_staff_role(self, guild: Guild) -> Role:
        return await self._get_role("staff", guild)


async def load(bot: Bot, database: Database) -> None:
    await database.add_table(Roles(bot, database))

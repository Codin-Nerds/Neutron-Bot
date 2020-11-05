import typing as t

from discord import Guild, Member, Role
from loguru import logger

from bot.core.bot import Bot
from bot.database import DBTable, Database


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

        try:
            return record[0]
        except TypeError:
            return None

    async def _get_time(self, time_permission: str, guild: t.Union[Guild, int], identifier: t.Union[Member, Role, int]) -> t.Optional[int]:
        if isinstance(identifier, int):
            user = self.bot.get_user(identifier)
            if not user:
                return await self._get_permission(time_permission, guild, identifier)

            if isinstance(guild, int):
                true_guild = self.bot.get_guild(guild)
                if not true_guild:
                    raise RuntimeError(f"Unable to find a guild with id: {guild}")
                guild = true_guild

            identifier = guild.get_member(user.id)

        if isinstance(identifier, Member):
            if identifier.guild_permissions.administrator:
                return -1

            # Follow role hierarchy from most important role to everyone
            # and use the first found time, if non is found, return `None`
            for role in identifier.roles[::-1]:
                time = await self._get_permission(time_permission, guild, role)
                if time is not None and time != 0:
                    return time
            else:
                return None

        if isinstance(identifier, Role):
            return await self._get_permission(time_permission, guild, identifier)

    async def _set_time(self, time_permission: str, guild: t.Union[Guild, int], role: t.Union[Role, int], value: t.Union[int, float]) -> None:
        if value == float("inf"):
            value = -1

        if not isinstance(value, int):
            return RuntimeError(f"value must be an integer, got {type(value)}: {value}")

        await self._set_permission(time_permission, guild, role, value)

    async def set_bantime(self, guild: t.Union[Guild, int], role: t.Union[Role, int], value: t.Union[int, float]) -> None:
        await self._set_time("bantime", guild, role, value)

    async def set_mutetime(self, guild: t.Union[Guild, int], role: t.Union[Role, int], value: t.Union[int, float]) -> None:
        await self._set_time("mutetime", guild, role, value)

    async def set_locktime(self, guild: t.Union[Guild, int], role: t.Union[Role, int], value: t.Union[int, float]) -> None:
        await self._set_time("locktime", guild, role, value)

    async def get_bantime(self, guild: t.Union[Guild, int], identifier: t.Union[Member, Role, int]) -> t.Optional[int]:
        return await self._get_time("bantime", guild, identifier)

    async def get_mutetime(self, guild: t.Union[Guild, int], identifier: t.Union[Member, Role, int]) -> t.Optional[int]:
        return await self._get_time("mutetime", guild, identifier)

    async def get_locktime(self, guild: t.Union[Guild, int], identifier: t.Union[Member, Role, int]) -> t.Optional[int]:
        return await self._get_time("locktime", guild, identifier)


async def load(bot: Bot, database: Database) -> None:
    await database.add_table(Permissions(bot, database))

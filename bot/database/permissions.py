import typing as t

from discord import Guild, Role
from loguru import logger
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import Base, upsert


class Permissions(Base):
    __tablename__ = "permissions"

    guild = Column('guild', String, primary_key=True, nullable=False)
    role = Column('role', String, primary_key=True, nullable=False)

    ban_time = Column('ban_time', Integer, nullable=True)
    mute_time = Column('mute_time', Integer, nullable=True)
    lock_time = Column('lock_time', Integer, nullable=True)

    @staticmethod
    def _get_str_guild(guild: t.Union[str, int, Guild]) -> str:
        """Make sure `guild` parameter is string."""
        if isinstance(guild, Guild):
            guild = str(guild.id)
        if isinstance(guild, int):
            guild = str(guild)
        return guild

    @staticmethod
    def _get_str_role(channel: t.Union[str, int, Role]) -> str:
        """Make sure `channel` parameter is string."""
        if isinstance(channel, Role):
            channel = str(channel.id)
        if isinstance(channel, int):
            channel = str(channel)
        return channel

    @staticmethod
    def _get_int_time(time: t.Union[int, float]) -> int:
        """Make sure to return time as int (seconds), or -1 for infinity."""
        if time == float("inf"):
            return -1
        if isinstance(time, float):
            return round(time)
        return time

    @staticmethod
    def _return_time(time: int) -> t.Union[int, float]:
        """Return infinity if number was -1, otherwise, return given number."""
        if time == -1:
            return float("inf")
        return time

    @staticmethod
    def _get_normalized_time_type(time_type: str) -> str:
        """Make sure `time_type` is in proper format and is valid."""
        time_type = time_type if time_type.endswith("_time") else time_type + "_time"

        valid_time_types = ["ban_time", "mute_time", "lock_time"]
        if time_type not in valid_time_types:
            raise ValueError(f"`time_type` received invalid type: {time_type}, valid types: {', '.join(valid_time_types)}")

        return time_type

    @classmethod
    async def set_role_permission(
        cls,
        session: AsyncSession,
        time_type: str,
        guild: t.Union[str, int, Guild],
        role: t.Union[str, int, Role],
        time: t.Union[int, float]
    ) -> None:
        """Store given `time` as `time_type` permission for `role` on `guild` into the database."""
        guild = cls._get_str_guild(guild)
        role = cls._get_str_role(role)
        time_type = cls._get_normalized_time_type(time_type)
        time = cls._get_int_time(time)

        logger.debug(f"Setting {time_type} for {role} on {guild} to {time}")

        await upsert(
            session, cls,
            conflict_columns=["role", "guild"],
            values={"guild": guild, "role": role, time_type: time}
        )

    @classmethod
    async def get_permissions(cls, session: AsyncSession, guild: t.Union[str, int, Guild], role: t.Union[str, int, Role]) -> dict:
        """Obtain permissions for `role` on `guild` from the database."""
        guild = cls._get_str_guild(guild)
        role = cls._get_str_role(role)

        row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild, role=role).one())
        row["ban_time"] = cls._return_time(row["ban_time"])
        row["mute_time"] = cls._return_time(row["mute_time"])
        row["lock_time"] = cls._return_time(row["lock_time"])
        return dict(row)

    @classmethod
    async def get_permission(cls, session: AsyncSession, time_type: str, guild: t.Union[str, int, Guild], role: t.Union[str, int, Role]) -> str:
        """Obtain`time_type` permissions for `role` on `guild` from the database."""
        time_type = cls._get_normalized_time_type(time_type)

        permissions = await cls.get_permissions(session, guild, role)
        return permissions[time_type]

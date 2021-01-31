import typing as t

from discord import Guild, Member, Role
from loguru import logger
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.bot import Bot
from bot.database import Base, upsert


class Permissions(Base):
    __tablename__ = "permissions"

    guild = Column(String, primary_key=True, nullable=False)
    role = Column(String, primary_key=True, nullable=False)

    ban_time = Column(Integer, nullable=True)
    mute_time = Column(Integer, nullable=True)
    lock_time = Column(Integer, nullable=True)

    @staticmethod
    def _get_str_guild(guild: t.Union[str, int, Guild]) -> str:
        """Make sure `guild` parameter is string."""
        if isinstance(guild, Guild):
            guild = str(guild.id)
        if isinstance(guild, int):
            guild = str(guild)
        return guild

    @staticmethod
    def _get_str_role(role: t.Union[str, int, Role]) -> str:
        """Make sure `role` parameter is string."""
        if isinstance(role, Role):
            role = str(role.id)
        if isinstance(role, int):
            role = str(role)
        return role

    @staticmethod
    def _get_int_time(time: t.Union[int, float]) -> int:
        """Make sure to return time as int (seconds), or -1 for infinity."""
        if time == float("inf"):
            return -1
        if isinstance(time, float):
            return round(time)
        return time

    @staticmethod
    def _return_time(time: t.Optional[int]) -> t.Optional[t.Union[int, float]]:
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
        await session.commit()

    @classmethod
    async def get_permissions(cls, session: AsyncSession, guild: t.Union[str, int, Guild], role: t.Union[str, int, Role]) -> dict:
        """Obtain permissions for `role` on `guild` from the database."""
        guild = cls._get_str_guild(guild)
        role = cls._get_str_role(role)

        try:
            row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild, role=role).one())
        except NoResultFound:
            return {
                "ban_time": None,
                "mute_time": None,
                "lock_time": None,
            }
        else:
            return {
                "ban_time": cls._return_time(row.ban_time),
                "mute_time": cls._return_time(row.mute_time),
                "lock_time": cls._return_time(row.lock_time),
            }

    @classmethod
    async def get_permission(
        cls,
        session: AsyncSession,
        time_type: str,
        guild: t.Union[str, int, Guild],
        role: t.Union[str, int, Role]
    ) -> t.Optional[int]:
        """Obtain`time_type` permissions for `role` on `guild` from the database."""
        time_type = cls._get_normalized_time_type(time_type)

        permissions = await cls.get_permissions(session, guild, role)
        return permissions[time_type]

    @classmethod
    async def get_permissions_from_member(
        cls,
        session: AsyncSession,
        bot: Bot,
        guild: t.Union[str, int, Guild],
        member: t.Union[str, int, Member]
    ) -> dict:
        if isinstance(guild, str):
            guild = int(guild)
        if isinstance(member, str):
            member = int(member)

        if isinstance(member, int):
            user = bot.get_user(member)
            if not user:
                raise ValueError(f"Unable to find valid user by: {member}")
            if isinstance(guild, int):
                true_guild = bot.get_guild(guild)
                if not true_guild:
                    raise ValueError(f"Unable to find a guild with id: {guild}")

            member = guild.get_member(user)

        if isinstance(member, Member):
            # Administrators doesn't have limited permissions, makes sure
            # to handle for that
            if member.guild_permissions.administrator:
                return {
                    "ban_time": float("inf"),
                    "mute_time": float("inf"),
                    "lock_time": float("inf"),
                }

            # Follow the hierarchy from most important role to everyone
            # and use the first found time in each time type,
            # if none found, return empty permissions
            ban_time = None
            mute_time = None
            lock_time = None
            for role in member.roles[::-1]:
                perms = await cls.get_permissions(session, guild, role)
                if ban_time is None:
                    ban_time = perms["ban_time"]
                if mute_time is None:
                    mute_time = perms["mute_time"]
                if lock_time is None:
                    lock_time = perms["lock_time"]

            return {
                "ban_time": ban_time,
                "mute_time": mute_time,
                "lock_time": lock_time,
            }

    @classmethod
    async def get_permission_from_member(
        cls,
        session: AsyncSession,
        bot: Bot,
        time_type: str,
        guild: t.Union[str, int, Guild],
        member: t.Union[str, int, Member]
    ) -> t.Optional[int]:
        time_type = cls._get_normalized_time_type(time_type)

        permissions = await cls.get_permissions_from_member(session, bot, guild, member)
        return permissions[time_type]

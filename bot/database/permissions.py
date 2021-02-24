import typing as t

from discord import Guild, Member, Role
from loguru import logger
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bot.core.bot import Bot
from bot.database import Base, get_str_guild, get_str_role, upsert


class Permissions(Base):
    __tablename__ = "permissions"

    guild = Column(String, primary_key=True, nullable=False)
    role = Column(String, primary_key=True, nullable=False)

    ban_time = Column(Integer, nullable=True)
    mute_time = Column(Integer, nullable=True)
    lock_time = Column(Integer, nullable=True)

    valid_time_types = ["ban_time", "mute_time", "lock_time"]

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

    @classmethod
    def _get_normalized_time_type(cls, time_type: str) -> str:
        """Make sure `time_type` is in proper format and is valid."""
        time_type = time_type if time_type.endswith("_time") else time_type + "_time"

        if time_type not in cls.valid_time_types:
            raise ValueError(f"`time_type` received invalid type: {time_type}, valid types: {', '.join(cls.valid_time_types)}")

        return time_type

    @classmethod
    async def set_role_permission(
        cls,
        engine: AsyncEngine,
        time_type: str,
        guild: t.Union[str, int, Guild],
        role: t.Union[str, int, Role],
        time: t.Union[int, float]
    ) -> None:
        """Store given `time` as `time_type` permission for `role` on `guild` into the database."""
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)
        role = get_str_role(role)
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
    async def get_permissions(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild], role: t.Union[str, int, Role]) -> dict:
        """Obtain permissions for `role` on `guild` from the database."""
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)
        role = get_str_role(role)

        try:
            row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild, role=role).one())
        except NoResultFound:
            dct = {col: None for col in cls.__table__.columns.keys()}
            dct.update({'guild': guild, 'role': role})
            return dct
        else:
            return row.to_dict()

    @classmethod
    async def get_permission(
        cls,
        engine: AsyncEngine,
        time_type: str,
        guild: t.Union[str, int, Guild],
        role: t.Union[str, int, Role]
    ) -> t.Optional[int]:
        """Obtain`time_type` permissions for `role` on `guild` from the database."""
        time_type = cls._get_normalized_time_type(time_type)

        permissions = await cls.get_permissions(engine, guild, role)
        return permissions[time_type]

    @classmethod
    async def get_permissions_from_member(
        cls,
        engine: AsyncEngine,
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
                dct = {col: float("inf") for col in cls.__table__.columns.keys()}
                dct.update({'guild': guild})
                return dct

            # Follow the hierarchy from most important role to everyone
            # and use the first found time in each time type,
            # if none found, return empty permissions
            dct = {col: None for col in cls.__table__.columns.keys() if col.endswith("_time")}
            for role in member.roles[::-1]:
                perms = await cls.get_permissions(engine, guild, role)
                for key, value in dct:
                    if value is not None:
                        dct[key] = perms[key]
            dct.update({'guild': guild})
            return dct

    @classmethod
    async def get_permission_from_member(
        cls,
        engine: AsyncEngine,
        bot: Bot,
        time_type: str,
        guild: t.Union[str, int, Guild],
        member: t.Union[str, int, Member]
    ) -> t.Optional[int]:
        time_type = cls._get_normalized_time_type(time_type)

        permissions = await cls.get_permissions_from_member(engine, bot, guild, member)
        return permissions[time_type]

    def to_dict(self) -> dict:
        dct = {}
        for col in self.__table__.columns.keys():
            val = getattr(self, col)
            if col.endswith("_time"):
                val = self._return_time(val)
            dct[col] = val
        return dct

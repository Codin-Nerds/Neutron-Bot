import typing as t

from discord import Guild, Role
from loguru import logger
from sqlalchemy import Column, String
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bot.database import Base, get_str_guild, get_str_role, upsert


class Roles(Base):
    __tablename__ = "roles"

    guild = Column(String, primary_key=True, nullable=False)

    default_role = Column(String, nullable=True)
    muted_role = Column(String, nullable=True)
    staff_role = Column(String, nullable=True)

    valid_role_types = ["default_role", "muted_role", "staff_role"]

    @classmethod
    def _get_normalized_role_type(cls, role_type: str) -> str:
        """Make sure `role_type` is in proper format and is valid."""
        role_type = role_type if role_type.endswith("_role") else role_type + "_role"

        if role_type not in cls.valid_role_types:
            raise ValueError(f"`role_type` received invalid type: {role_type}, valid types: {', '.join(cls.valid_role_types)}")

        return role_type

    @classmethod
    async def set_role(
        cls,
        engine: AsyncEngine,
        role_type: str,
        guild: t.Union[str, int, Guild],
        role: t.Union[str, int, Role],
    ) -> None:
        """Store given `role` as `role_type` role for on `guild` into the database."""
        session = AsyncSession(bind=engine)

        role_type = cls._get_normalized_role_type(role_type)
        guild = get_str_guild(guild)
        role = get_str_role(role)

        logger.debug(f"Setting {role_type} on {guild} to {role}")

        await upsert(
            session, cls,
            conflict_columns=["guild"],
            values={"guild": guild, role_type: role}
        )
        await session.commit()
        await session.close()

    @classmethod
    async def get_roles(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild]) -> dict:
        """Obtain roles on `guild` from the database."""
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)
        try:
            row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild).one())
        except NoResultFound:
            dct = {col: None for col in cls.__table__.columns.keys()}
            dct.update({'guild': guild})
            return dct
        else:
            return row.to_dict()
        finally:
            await session.close()

    @classmethod
    async def get_role(cls, engine: AsyncEngine, role_type: str, guild: t.Union[str, int, Guild]) -> str:
        """Obtain`time_type` permissions for `role` on `guild` from the database."""
        role_type = cls._get_normalized_role_type(role_type)

        roles = await cls.get_roles(engine, guild)
        return roles[role_type]

    def to_dict(self) -> dict:
        dct = {}
        for col in self.__table__.columns.keys():
            val = getattr(self, col)
            if col.endswith("_role"):
                val = int(val) if val is not None else None
            dct[col] = val
        return dct

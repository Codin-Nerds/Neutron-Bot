import typing as t

from discord import Guild, Role
from loguru import logger
from sqlalchemy import Column, String
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import Base, upsert


class Roles(Base):
    __tablename__ = "roles"

    guild = Column('guild', String, primary_key=True, nullable=False)

    default_role = Column('default_role', String, nullable=True)
    muted_role = Column('muted_role', String, nullable=True)
    staff_role = Column('staff_role', String, nullable=True)

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
    def _get_normalized_role_type(role_type: str) -> str:
        """Make sure `role_type` is in proper format and is valid."""
        role_type = role_type if role_type.endswith("_role") else role_type + "_role"

        valid_role_types = ["default_role", "muted_role", "staff_role"]
        if role_type not in valid_role_types:
            raise ValueError(f"`role_type` received invalid type: {role_type}, valid types: {', '.join(valid_role_types)}")

        return role_type

    @classmethod
    async def set_role(
        cls,
        session: AsyncSession,
        role_type: str,
        guild: t.Union[str, int, Guild],
        role: t.Union[str, int, Role],
    ) -> None:
        """Store given `role` as `role_type` role for on `guild` into the database."""
        guild = cls._get_str_guild(guild)
        role = cls._get_str_role(role)

        logger.debug(f"Setting {role_type} on {guild} to {role}")

        await upsert(
            session, cls,
            conflict_columns=["guild"],
            values={"guild": guild, role_type: role}
        )
        await session.commit()

    @classmethod
    async def get_roles(cls, session: AsyncSession, guild: t.Union[str, int, Guild]) -> dict:
        """Obtain roles on `guild` from the database."""
        guild = cls._get_str_guild(guild)

        row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild).one())
        return {
            "default_role": int(row.default_role) if row.default_role else None,
            "muted_role": int(row.muted_role) if row.muted_role else None,
            "staff_role": int(row.staff_role) if row.staff_role else None,
        }

    @classmethod
    async def get_role(cls, session: AsyncSession, role_type: str, guild: t.Union[str, int, Guild]) -> str:
        """Obtain`time_type` permissions for `role` on `guild` from the database."""
        role_type = cls._get_normalized_role_type(role_type)

        permissions = await cls.get_roles(session, guild)
        return permissions[role_type]

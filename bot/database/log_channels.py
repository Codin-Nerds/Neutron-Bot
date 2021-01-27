import typing as t

from discord import Guild, TextChannel
from loguru import logger
from sqlalchemy import Column, String
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import Base, upsert


class LogChannels(Base):
    __tablename__ = "log_channels"

    guild = Column('guild', String, primary_key=True, nullable=False)

    server_log = Column('server_log', String, nullable=True)
    mod_log = Column('mod_log', String, nullable=True)
    message_log = Column('message_log', String, nullable=True)
    member_log = Column('member_log', String, nullable=True)
    join_log = Column('join_log', String, nullable=True)

    @staticmethod
    def _get_str_guild(guild: t.Union[str, int, Guild]) -> str:
        """Make sure `guild` parameter is string."""
        if isinstance(guild, Guild):
            guild = str(guild.id)
        if isinstance(guild, int):
            guild = str(guild)
        return guild

    @staticmethod
    def _get_str_channel(channel: t.Union[str, int, TextChannel]) -> str:
        """Make sure `channel` parameter is string."""
        if isinstance(channel, TextChannel):
            channel = str(channel.id)
        if isinstance(channel, int):
            channel = str(channel)
        return channel

    @classmethod
    def _get_normalized_log_type(log_type: str) -> str:
        """Make sure `log_type` is in proper format and is valid."""
        log_type = log_type if log_type.endswith("_log") else log_type + "_log"

        valid_log_types = ["server_log", "mod_log", "message_log", "member_log", "join_log"]
        if log_type not in valid_log_types:
            raise ValueError(f"`log_type` received invalid type: {log_type}, valid types: {', '.join(valid_log_types)}")

        return log_type

    @classmethod
    async def set_log_channel(
        cls,
        session: AsyncSession,
        log_type: str,
        guild: t.Union[str, int, Guild],
        channel: t.Union[str, int, TextChannel]
    ) -> None:
        """Store given `channel` as `log_type` log channel for `guild` into the database."""
        guild = cls._get_str_guild(guild)
        channel = cls._get_str_channel(channel)
        log_type = cls._get_normalized_log_type(log_type)

        logger.debug(f"Setting {log_type} channel on {guild} to <#{channel}>")

        await upsert(
            session, cls,
            conflict_columns=["guild"],
            values={"guild": guild, log_type: channel}
        )

    @classmethod
    async def get_log_channel(cls, session: AsyncSession, log_type: str, guild: t.Union[str, int, Guild]) -> str:
        """Obtain given `log_type` log channel for `guild` from the database."""
        guild = cls._get_str_guild(guild)
        log_type = cls._get_normalized_log_type(log_type)

        row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild).one())
        return getattr(row, log_type)

import typing as t

from discord import Guild, TextChannel
from loguru import logger
from sqlalchemy import Column, String
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bot.database import Base, get_str_channel, get_str_guild, upsert


class LogChannels(Base):
    __tablename__ = "log_channels"

    guild = Column(String, primary_key=True, nullable=False)

    server_log = Column(String, nullable=True)
    mod_log = Column(String, nullable=True)
    message_log = Column(String, nullable=True)
    member_log = Column(String, nullable=True)
    join_log = Column(String, nullable=True)
    voice_log = Column(String, nullable=True)

    valid_log_types = ["server_log", "mod_log", "message_log", "member_log", "join_log", "voice_log"]

    @classmethod
    def _get_normalized_log_type(cls, log_type: str) -> str:
        """Make sure `log_type` is in proper format and is valid."""
        log_type = log_type if log_type.endswith("_log") else log_type + "_log"

        if log_type not in cls.valid_log_types:
            raise ValueError(f"`log_type` received invalid type: {log_type}, valid types: {', '.join(cls.valid_log_types)}")

        return log_type

    @classmethod
    async def set_log_channel(
        cls,
        engine: AsyncEngine,
        log_type: str,
        guild: t.Union[str, int, Guild],
        channel: t.Union[str, int, TextChannel]
    ) -> None:
        """Store given `channel` as `log_type` log channel for `guild` into the database."""
        session = AsyncSession(engine)

        guild = get_str_guild(guild)
        channel = get_str_channel(channel)
        log_type = cls._get_normalized_log_type(log_type)

        logger.debug(f"Setting {log_type} channel on {guild} to <#{channel}>")

        await upsert(
            session, cls,
            conflict_columns=["guild"],
            values={"guild": guild, log_type: channel}
        )
        await session.commit()
        await session.close()

    @classmethod
    async def get_log_channels(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild]) -> dict:
        """Obtain defined log channels for given `guild` from the database."""
        session = AsyncSession(engine)

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
    async def get_log_channel(cls, engine: AsyncEngine, log_type: str, guild: t.Union[str, int, Guild]) -> dict:
        log_type = cls._get_normalized_log_type(log_type)

        log_channels = await cls.get_log_channels(engine, guild)
        return log_channels[log_type]

    def to_dict(self) -> dict:
        dct = {}
        for col in self.__table__.columns.keys():
            val = getattr(self, col)
            if col.endswith("_log"):
                val = int(val) if val is not None else None
            dct[col] = val
        return dct

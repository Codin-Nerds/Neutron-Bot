import typing as t

from discord import Guild, TextChannel
from loguru import logger
from sqlalchemy import Column, String
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bot.config import LogChannelType
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

    @classmethod
    async def set_log_channel(
        cls,
        engine: AsyncEngine,
        log_type: LogChannelType,
        guild: t.Union[str, int, Guild],
        channel: t.Union[str, int, TextChannel]
    ) -> None:
        """Store given `channel` as `log_type` log channel for `guild` into the database."""
        session = AsyncSession(engine)

        guild = get_str_guild(guild)
        channel = get_str_channel(channel)

        logger.debug(f"Setting {log_type.value} channel on {guild} to <#{channel}>")

        await upsert(
            session, cls,
            conflict_columns=["guild"],
            values={"guild": guild, log_type.value: channel}
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
            dct = {col: None for col in LogChannelType.__members__}
            dct.update(guild=guild)
            return dct
        else:
            return row.to_dict()
        finally:
            await session.close()

    @classmethod
    async def get_log_channel(cls, engine: AsyncEngine, log_type: LogChannelType, guild: t.Union[str, int, Guild]) -> dict:
        log_channels = await cls.get_log_channels(engine, guild)
        return log_channels[log_type]

    def to_dict(self) -> dict:
        dct = {}
        for col in self.__table__.columns.keys():
            val = getattr(self, col)
            if col.endswith("_log"):
                val = int(val) if val is not None else None
                col = LogChannelType.__members__[col]
            dct[col] = val
        return dct

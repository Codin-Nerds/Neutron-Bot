import typing as t

from discord import Guild, Member, User
from loguru import logger
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bot.database import Base, get_str_guild, get_str_user, upsert


class StrikeIndex(Base):
    __tablename__ = "strike_index"

    guild = Column(String, primary_key=True, nullable=False)
    next_id = Column(Integer, nullable=False, default=0)

    @classmethod
    async def get_id(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild]) -> int:
        session = AsyncSession(bind=engine)
        guild = get_str_guild(guild)

        # Logic for increasing strike ID if it was already found
        # but using the default if the entry is new
        row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild).one())
        next_id = row.next_id + 1
        row.next_id = next_id
        await session.commit()
        await session.close()
        return next_id


class Strikes(Base):
    __tablename__ = "strikes"

    guild = Column(String, primary_key=True, nullable=False)
    id = Column(Integer, primary_key=True, nullable=False)

    author = Column(String, nullable=False)
    user = Column(String, nullable=False)
    type = Column(String, nullable=False)
    reason = Column(String, nullable=True)

    @classmethod
    async def set_strike(
        cls,
        engine: AsyncEngine,
        guild: t.Union[str, int, Guild],
        author: t.Union[str, int, Member],
        user: t.Union[str, int, Member, User],
        strike_type: str,
        reason: t.Optional[str],
        strike_id: t.Optional[int] = None
    ) -> int:
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)
        author = get_str_user(author)
        user = get_str_user(user)

        # We don't usually expect we have passed id, instead we're determining
        # which ID should be used from the index table to keep the strikes serial
        # with their specific guild, if strike is specified, it means we're updating
        if not strike_id:
            strike_id = await StrikeIndex.get_id(session, guild)

        logger.debug(f"Adding {strike_type} strike to {user} from {author} for {reason}: id: {strike_id}")

        await upsert(
            session, cls,
            conflict_columns=["guild", "id"],
            values={
                "guild": guild,
                "id": strike_id,
                "author": author,
                "user": user,
                "type": strike_type,
                "reason": reason
            }
        )
        await session.commit()
        await session.close()
        return strike_id

    @classmethod
    async def remove_strike(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild], strike_id: int) -> dict:
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)

        row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild, id=strike_id).one())
        dct = row.to_dict()
        await session.run_sync(lambda session: session.delete(row))
        await session.close()

        logger.debug(f"Strike {strike_id} has been removed")

        return dct

    @classmethod
    async def get_user_strikes(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild], user: t.Union[str, int, Member, User]) -> list:
        """Obtain all strikes on `guild` for `user` from the database."""
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)
        user = get_str_user(user)

        try:
            rows = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild, user=user).all())
        except NoResultFound:
            return []
        else:
            strikes = []
            for row in rows:
                strikes.append(row.to_dict())
            return strikes
        finally:
            await session.close()

    @classmethod
    async def get_author_strikes(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild], author: t.Union[str, int, Member, User]) -> list:
        """Obtain all strikes on `guild` by `author` from the database."""
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)
        author = get_str_user(author)

        try:
            rows = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild, author=author).all())
        except NoResultFound:
            return []
        else:
            strikes = []
            for row in rows:
                strikes.append(row.to_dict())
            return strikes
        finally:
            await session.close()

    @classmethod
    async def get_strike_by_id(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild], strike_id: int) -> dict:
        """Obtain specific strike in `guild` with id of `strike_id` from the database."""
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)

        try:
            row = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild, id=strike_id).one())
        except NoResultFound:
            dct = {col: None for col in cls.__table__.columns.keys()}
            dct.update({'guild': guild, 'id': strike_id})
            return dct
        else:
            return row.to_dict()
        finally:
            await session.close()

    @classmethod
    async def get_guild_strikes(cls, engine: AsyncEngine, guild: t.Union[str, int, Guild]) -> list:
        """Obtain all strikes belonging to `guild` from the database."""
        session = AsyncSession(bind=engine)

        guild = get_str_guild(guild)

        try:
            rows = await session.run_sync(lambda session: session.query(cls).filter_by(guild=guild).all())
        except NoResultFound:
            return []
        else:
            strikes = []
            for row in rows:
                strikes.append(row.to_dict())
            return strikes
        finally:
            session.close()

    def to_dict(self) -> dict:
        dct = {}
        for col in self.__table__.columns.keys():
            val = getattr(self, col)
            if col in ("user", "author"):
                val = int(val) if val is not None else None
            dct[col] = val
        return dct

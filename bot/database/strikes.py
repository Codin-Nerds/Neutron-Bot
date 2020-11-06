import typing as t
from dataclasses import dataclass

from discord import Guild, User
from loguru import logger

from bot.config import STRIKE_TYPES
from bot.core.bot import Bot
from bot.database import DBTable, Database


@dataclass
class Entry:
    """Class for storing the database rows of roles table."""
    serverid: int
    strike_id: int
    author: int
    subject: int
    strike_type: str
    reason: str


class Strikes(DBTable):
    """
    This table stores all strikes/infractions in each guild.
    * `author` ID of user who gave the infraction
    * `subject` ID of user who received the strike
    * `reason` optional reason string
    For given `strike_id` in given`serverid`
    """
    columns = {
        "serverid": "NUMERIC(40) NOT NULL",
        "strike_id": "SERIAL NOT NULL",
        "author": "NUMERIC(40) DEFAULT 0",
        "subject": "NUMERIC(40) DEFAULT 0",
        "strike_type": "TEXT NOT NULL",
        "reason": "TEXT",
        "UNIQUE": "(serverid, strike_id)"
    }

    def __init__(self, bot: Bot, database: Database):
        super().__init__(database, "strikes")
        self.bot = bot
        self.database = database

    async def add_strike(
        self,
        guild: t.Union[Guild, int],
        author: t.Union[User, int],
        subject: t.Union[User, int],
        strike_type: STRIKE_TYPES,
        reason: str = "None"
    ) -> None:
        """Set a `role_name` column to store `role` for the specific `guild`."""
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(subject, User):
            subject = subject.id
        if isinstance(author, User):
            author = author.id

        logger.debug(f"Adding {strike_type} strike to {subject} from {author} for {reason}")
        await self.db_set(
            columns=["serverid", "author", "subject", "strike_type", "reason"],
            values=[guild, author, subject, strike_type, reason]
        )

    async def get_strike(self, guild: t.Union[Guild, int], strike_id: int) -> int:
        """Get a `role_name` column for specific `guild` from cache."""
        if isinstance(guild, Guild):
            guild = guild.id

        record = await self.db_get(
            columns=["author", "subject", "strike_type", "reason"],
            specification="serverid=$1 AND strike_id=$2",
            sql_args=[guild, strike_id]
        )

        try:
            return record[0]
        except TypeError:
            return None

    async def update_strike(
        self,
        guild: t.Union[Guild, int],
        strike_id: int,
        author: t.Union[User, int],
        subject: t.Union[User, int],
        strike_type: STRIKE_TYPES,
        reason: str
    ) -> None:
        """Set a `role_name` column to store `role` for the specific `guild`."""
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(subject, User):
            subject = subject.id
        if isinstance(author, User):
            author = author.id

        logger.debug(f"Adding {strike_type} strike to {subject} from {author} for {reason}")
        await self.db_upsert(
            columns=["serverid", "strike_id", "author", "subject", "strike_type", "reason"],
            values=[guild, strike_id, author, subject, strike_type, reason],
            conflict_columns=["serverid", "strike_id"]
        )

    async def get_guild_strikes(self, guild: t.Union[Guild, int]) -> t.List[Entry]:
        if isinstance(guild, Guild):
            guild = guild.id

        record = await self.db_get(
            columns=["strike_id", "author", "subject", "strike_type", "reason"],
            specification="serverid=$1",
            sql_args=[guild]
        )

        try:
            return record[0]
        except TypeError:
            return None

    async def get_user_strikes(self, guild: t.Union[Guild, int], subject: t.Union[User, int]) -> t.List[Entry]:
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(subject, User):
            subject = subject.id

        record = await self.db_get(
            columns=["strike_id", "author", "subject", "strike_type", "reason"],
            specification="serverid=$1 AND subject=$2",
            sql_args=[guild, subject]
        )

        try:
            return record[0]
        except TypeError:
            return None

    async def get_authored_strikes(self, guild: t.Union[Guild, int], author: t.Union[User, int]) -> t.List[Entry]:
        if isinstance(guild, Guild):
            guild = guild.id
        if isinstance(author, User):
            author = author.id

        record = await self.db_get(
            columns=["strike_id", "author", "subject", "strike_type", "reason"],
            specification="serverid=$1 AND author=$2",
            sql_args=[guild, author]
        )

        try:
            return record[0]
        except TypeError:
            return None


async def load(bot: Bot, database: Database) -> None:
    await database.add_table(Strikes(bot, database))

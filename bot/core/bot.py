import time
import typing as t
from collections import defaultdict
from datetime import datetime

import aiohttp
from asyncpg.exceptions import InvalidPasswordError
from discord.ext.commands import AutoShardedBot as Base_Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from bot import config
from bot.config import Event
from bot.core.autoload import EXTENSIONS, readable_name
from bot.database import Base as DbBase
from bot.database import load_tables


class Bot(Base_Bot):
    """Subclassed Neutron bot."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the subclass."""
        super().__init__(*args, **kwargs)

        self.start_time = datetime.utcnow()
        self.initial_call = True
        self._ignored_log = defaultdict(set)

    async def load_extensions(self) -> None:
        """Load all listed cogs."""
        for extension in EXTENSIONS:
            try:
                self.load_extension(extension)
                logger.debug(f"Cog {readable_name(extension)} loaded.")
            except Exception as e:
                logger.error(f"Cog {readable_name(extension)} failed to load with {type(e)}: {e}")

    async def db_connect(self) -> AsyncEngine:
        """
        Estabolish connection with the database and return the asynchronous engine.

        Function which interract with database will then be able to use this engine to
        create their `AsyncSession` instances, which will then be used to perform any
        operations on the database.

        We retrun `AsyncEngine` instead of directly using `AsyncSession`, because reusing
        the same session isn't thread-safe and when multiple calls happen concurrently,
        it causes issues that asyncpg can't handle.
        """
        load_tables()  # Load all DB Tables, in order to bring them into the metadata of DbBase

        engine = create_async_engine(config.DATABASE_ENGINE_STRING)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(DbBase.metadata.create_all)  # Create all database tables from found models
        except ConnectionRefusedError:
            # Keep recursively trying to connect to the database
            logger.error("Unable to connect to database, retrying in 5s")
            time.sleep(5)
            return await self.db_connect()
        except InvalidPasswordError as exc:
            logger.critical("Invalid database password.")
            raise exc

        return engine

    async def on_ready(self) -> None:
        if self.initial_call:
            self.initial_call = False

            await self.load_extensions()

            logger.info("Bot is ready")
        else:
            logger.info("Bot connection reinitialized")

    def run(self, token: t.Optional[str]) -> None:
        """Override the default `run` method and add a missing token check"""
        if not token:
            logger.critical("Missing Bot Token!")
        else:
            super().run(token)

    async def start(self, *args, **kwargs) -> None:
        """
        Estabolish a session for sqlalchemy database and aiohttp.

        Overwriting `start` method is needed in order to only make a connection
        after the bot itself has been initiated.

        Setting these on `__init__` directly would mean in case the bot fails to run
        it won't be easy to close the connection.
        """
        self.http_session = aiohttp.ClientSession()
        self.db_engine = await self.db_connect()
        await super().start(*args, **kwargs)

    async def close(self) -> None:
        """Close the bot and do some cleanup."""
        logger.info("Closing bot connection")
        if hasattr(self, "http_session"):
            await self.http_session.close()
        await super().close()

    def log_ignore(self, event: Event, *items: t.Any) -> None:
        """
        Add event to the set of ignored events to abort log sending.

        This function is meant for other cogs, to use and add ignored events,
        which is useful, because if we trigger an action like banning with a command,
        we may have more information about that ban, than we would get from the listener.
        The cog that ignored some event can then send a log message directly, with this
        additional info.

        `items` can contain multiple uniquely identifiable keys for given events to be
        ignored. This unique key will then be used for checking if given even it ignored.
        """
        for item in items:
            if item not in self._ignored_log[event]:
                self._ignored_log[event].add(item)

    def log_is_ignored(self, event: Event, key: t.Any, remove: bool = True) -> bool:
        """
        Check if given event with uniquely identifiable `key` is present in
        the ignore set, if it is, return `True`, otherwise return `False`.

        By default, after this function is executed, the ignored entry will get removed,
        because we already applied ignore as this check was used. If this isn't the case,
        `remove` kwarg can be set to `False`, to prevent this automatic deletion.
        """
        found = key in self._ignored_log[event]
        if found and remove:
            self._ignored_log[event].remove(key)

        return found

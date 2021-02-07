import time
import typing as t
from datetime import datetime

import aiohttp
from asyncpg.exceptions import InvalidPasswordError
from discord.ext.commands import AutoShardedBot as Base_Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from bot import config
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

    async def load_extensions(self) -> None:
        """Load all listed cogs."""
        for extension in EXTENSIONS:
            try:
                self.load_extension(extension)
                logger.debug(f"Cog {readable_name(extension)} loaded.")
            except Exception as e:
                logger.error(f"Cog {readable_name(extension)} failed to load with {type(e)}: {e}")

    async def db_connect(self) -> AsyncSession:
        """Estabolish connection with the database and return the asynchronous session."""
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

        return AsyncSession(bind=engine)

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
            logger.error("Missing Bot Token!")
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
        self.db_session = await self.db_connect()
        await super().start(*args, **kwargs)

    async def close(self) -> None:
        """Close the bot and do some cleanup."""
        logger.info("Closing bot connection")
        if hasattr(self, "http_session"):
            await self.http_session.close()
        if hasattr(self, "db_session"):
            await self.db_session.close()
        await super().close()

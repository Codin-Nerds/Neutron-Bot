import time
from datetime import datetime

import aiohttp
from discord.ext.commands import AutoShardedBot as Base_Bot
from loguru import logger

from bot import config
from bot.database import Database


class Bot(Base_Bot):
    """Subclassed Neutron bot."""

    def __init__(self, extensions: list, db_tables: list, *args, **kwargs) -> None:
        """Initialize the subclass."""
        super().__init__(*args, **kwargs)

        self.start_time = datetime.utcnow()

        self.extension_list = extensions
        self.db_table_list = db_tables
        self.initial_call = True

    async def load_extensions(self) -> None:
        """Load all listed cogs."""
        for extension in self.extension_list:
            try:
                self.load_extension(extension)
                logger.debug(f"Cog {extension} loaded.")
            except Exception as e:
                logger.error(f"Cog {extension} failed to load with {type(e)}: {e}")

    async def db_connect(self) -> None:
        """Estabolish connection with the database."""
        self.database = Database(config.DATABASE)
        connected = await self.database.connect()
        while not connected:
            logger.warning("Retrying to connect to database in 5s")
            # Synchronous sleep function to stop everything until db is connecting
            time.sleep(5)
            connected = await self.database.connect()

        await self.database.load_tables(self.db_table_list, self)

    async def on_ready(self) -> None:
        if self.initial_call:
            self.initial_call = False

            await self.load_extensions()

            logger.info("Bot is ready")
        else:
            logger.info("Bot connection reinitialized")

    def run(self, token: str) -> None:
        """Override the default `run` method and add a missing token check"""
        if not token:
            logger.error("Missing Bot Token!")
        else:
            super().run(token)

    async def start(self, *args, **kwargs) -> None:
        """
        Estabolish a connection to asyncpg database and aiohttp session.

        Overwriting `start` method is needed in order to only make a connection
        after the bot itself has been initiated.

        Setting these on `__init__` directly would mean in case the bot fails to run
        it won't be easy to close the connection.
        """
        self.session = aiohttp.ClientSession()
        await self.db_connect()
        await super().start(*args, **kwargs)

    async def close(self) -> None:
        """Close the bot and do some cleanup."""
        logger.info("Closing bot connection")
        if hasattr(self, "session"):
            await self.session.close()
        if hasattr(self, "database") and hasattr(self.database, "pool"):
            await self.database.disconnect()
        await super().close()

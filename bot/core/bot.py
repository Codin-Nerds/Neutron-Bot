import time

import aiohttp
from discord.ext.commands import AutoShardedBot as Base_Bot
from loguru import logger

from bot import config
from bot.core.database import Database


class Bot(Base_Bot):
    """Subclassed Hotwired bot."""

    def __init__(self, extensions: list, *args, **kwargs) -> None:
        """Initialize the subclass."""
        super().__init__(*args, **kwargs)
        self.session = aiohttp.ClientSession()

        self.extension_list = extensions
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
        self.database = Database(**config.DATABASE)
        connected = await self.database.connect()
        while not connected:
            logger.warning("Retrying to connect to database in 5s")
            # Synchronous sleep function to stop everything until db is connecting
            time.sleep(5)
            connected = await self.database.connect()

    async def on_ready(self) -> None:
        if self.initial_call:
            self.initial_call = False

            await self.db_connect()
            await self.load_extensions()

            logger.info("Bot is ready")
        else:
            logger.info("Bot connection reinitialized")

    def run(self, token: str) -> None:
        if not token:
            logger.error("Missing Bot Token!")
        else:
            super().run(token)

    async def close(self) -> None:
        """Close the bot and do some cleanup."""
        logger.info("Closing bot connection")
        await self.session.close()
        await self.database.disconnect()
        await super().close()

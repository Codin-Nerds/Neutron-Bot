import aiohttp
from discord.ext.commands import AutoShardedBot as Base_Bot
from loguru import logger


class Bot(Base_Bot):
    """Subclassed Hotwired bot."""

    def __init__(self, extensions: list, *args, **kwargs) -> None:
        """Initialize the subclass."""
        super().__init__(*args, **kwargs)
        self.session = aiohttp.ClientSession()

        self.extension_list = extensions
        self.first_on_ready = True

    async def on_ready(self) -> None:
        """Initialize some stuff once the bot is ready."""
        if self.first_on_ready:
            self.first_on_ready = False

            # Load all extensions
            for extension in self.extension_list:
                with logger.catch(message=f"Cog {extension} failed to load"):
                    self.load_extension(extension)
                    logger.debug(f"Cog {extension} loaded.")

            logger.info("Bot is ready")
        else:
            logger.info("Bot connection reinitialized")

    async def close(self) -> None:
        """Close the bot and do some cleanup."""
        logger.info("Closing bot connection")
        await self.session.close()
        await super().close()

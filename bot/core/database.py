import asyncpg
from loguru import logger


class Singleton(type):
    """This is Singleton Design Pattern"""
    _instance = None

    def __call__(cls, *args, **kwargs):
        """If instance already exists, return it"""
        if not cls._instance:
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instance


class Database(metaclass=Singleton):
    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        min_size: int,
        max_size: int
    ):
        self.database = {
            "host": host,
            "database": database,
            "user": user,
            "password": password,
            "min_size": min_size,
            "max_size": max_size
        }
        self.timeout = 5

    async def connect(self) -> bool:
        logger.debug("Connecting to the database")
        try:
            self.pool = await asyncpg.create_pool(**self.database)
        except asyncpg.exceptions.PostgresError:
            logger.error("Unable to connect to the database")
            return False

        await self._populate()
        return True

    async def disconnect(self) -> bool:
        logger.debug("Closing connection to the database")
        await self.pool.close()

    async def _populate(self) -> None:
        commands = [
        ]

        logger.trace("Populating database")
        async with self.pool.acquire(timeout=self.timeout) as db:
            for command in commands:
                await db.execute(command)

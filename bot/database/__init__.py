import typing as t
from importlib import import_module

import asyncpg
from loguru import logger

if t.TYPE_CHECKING:
    from bot.core.bot import Bot


class Singleton(type):
    """This is Singleton Design Pattern"""
    _instance = None

    def __call__(cls, *args, **kwargs):
        """If instance already exists, return it"""
        if not cls._instance:
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instance


class DBTable(metaclass=Singleton):
    def __init__(self, db: "Database", table_name: str):
        self.database = db
        self.table = table_name
        self.pool = self.database.pool
        self.timeout = self.database.timeout

    async def _populate(self) -> None:
        """
        This method is used to create the initial table structure
        and define it's structure and columns.
        """
        if not hasattr(self, "populate_command"):
            logger.warning(f"Table {self.__class__} doesn't have a `populate_command` attribute set, skipping populating.")
            return

        logger.trace(f"Populating {self.__class__}")
        async with self.pool.acquire(timeout=self.timeout) as db:
            await db.execute(self.populate_command)

    @classmethod
    def reference(cls) -> "DBTable":
        return cls._instance

    async def db_execute(self, sql: str, sql_args: t.Optional[list] = None) -> None:
        if not sql_args:
            sql_args = []

        async with self.pool.acquire(timeout=self.timeout) as db:
            await db.execute(sql, *sql_args)

    async def db_fetch(self, sql: str, sql_args: t.Optional[list] = None) -> asyncpg.Record:
        if not sql_args:
            sql_args = []

        async with self.pool.acquire(timeout=self.timeout) as db:
            return await db.fetchrow(sql, *sql_args)

    async def db_get(self, column: str, specification: t.Optional[str] = None, sql_args: t.Optional[list] = None) -> asyncpg.Record:
        sql = f"SELECT {column} FROM {self.table}"
        if specification:
            sql += f" WHERE {specification}"

        await self.db_fetch(sql, sql_args)

    async def db_set(self, columns: t.List[str], values: t.List[str]) -> None:
        sql_columns = ", ".join(columns)
        sql_values = ", ".join(f"${n + 1}" for n in range(len(values)))

        sql = f"""
        INSERT INTO {self.table} ({sql_columns})
        VALUES ({sql_values})
        """

        await self.db_execute(sql, values)

    async def db_upsert(self, columns: t.List[str], values: t.List[str], conflict_column: str) -> None:
        sql_columns = ", ".join(columns)
        sql_values = ", ".join(f"${n + 1}" for n in range(len(values)))
        sql_update = ""
        for index, column in enumerate(columns):
            if column != conflict_column:
                sql_update += f"{column}=${index}"

        sql = f"""
        INSERT INTO {self.table} ({sql_columns})
        VALUES ({sql_values})
        ON CONFLICT ({conflict_column}) DO
        UPDATE SET {sql_update}
        """

        await self.db_execute(sql, values)


class Database(metaclass=Singleton):
    def __init__(
        self,
        db_parameters: dict,
        timeout: int = 5
    ):
        required_parameters = set(["host", "database", "user", "password"])
        # Make sure db_parameters contains all required keys by checking
        # if it's a subset of `required_parameters`
        if required_parameters > set(db_parameters.keys()):
            raise RuntimeError(
                "The `db_parameters` dict doesn't contain one or more"
                f" of the required parameters: {required_parameters}"
            )

        self.db_parameters = db_parameters
        self.timeout = 5

        self.tables = set()

    async def connect(self) -> bool:
        logger.debug("Connecting to the database")
        try:
            self.pool = await asyncpg.create_pool(**self.db_parameters)
        except asyncpg.exceptions.PostgresError:
            logger.error("Unable to connect to the database")
            return False

        return True

    async def disconnect(self) -> bool:
        logger.debug("Closing connection to the database")
        await self.pool.close()

    async def add_tables(self, tables: t.List[str], bot: "Bot") -> None:
        for table in tables:
            logger.trace(f"Adding {table} table")
            module = import_module(table)
            if not hasattr(module, "load"):
                logger.error(f"Unable to load table: {table} (this: {__name__} module: {module}), it doesn't have the async `load` function set up")
                return
            await module.load(bot, self)

    async def load_table(self, table: DBTable) -> None:
        if table in self.tables:
            logger.warning(f"Tried to add already added table ({table.__class__}), skipping.")
            return
        if not isinstance(table, DBTable):
            raise TypeError("`table` argument must be an instance of `DBTable`")

        self.tables.add(table)
        await table._populate()

    async def remove_table(self, table: "DBTable") -> None:
        if table not in self.tables:
            logger.warning(f"Tried to remove unknown table ({table.__class__})")

        logger.trace(f"Removing {table.__class__}")
        self.tables.remove(table)
        table._instance = None

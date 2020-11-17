import typing as t
from abc import abstractmethod
from collections import defaultdict
from contextlib import suppress
from dataclasses import field, make_dataclass
from importlib import import_module

import asyncpg
from loguru import logger

if t.TYPE_CHECKING:
    from bot.core.bot import Bot


class Singleton(type):
    """
    This is Singleton Design Pattern.

    It makes sure that classes with this metaclass
    will only ever have one single instance, when they're
    initiated for the first time this instance is created,
    every next initiation will simply result in returning
    the stored single instace.
    """
    _instance = None

    def __call__(cls, *args, **kwargs):
        """If instance already exists, return it."""
        if not cls._instance:
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instance


class DBTable(metaclass=Singleton):
    """
    This is a basic database table structure model.

    This class automatically creates the initial database
    tables accordingly to `columns` dict which is a mandantory
    class parameter defined in the top-level class, it should
    look like this:
    columns = {
        "column_name": "SQL creation syntax",
        "example": "NUMERIC(40) UNIQUE NOT NULL"
        ...
    }

    After the table is populated, caching will be automatically
    set up based on the `caching` dict which is an optional class
    parameter defined in the top-level class, if this parameter isn't
    defined, caching will be skipped. Example for caching:
    caching = {
        "key": "table_name",  # This will be the key for the stored `cache` dict

        # These will be the entries for the cache
        "column_name": (python datatype, default_value),
        "column_name2": python datatype  # default_value is optional
    }

    There are also multiple methods which serves as an abstraction
    layer for for executing raw SQL code.

    There is also a special `reference` classmethod which will
    return the running instance (from the singleton model).
    """
    def __init__(self, db: "Database", table_name: str):
        self.database = db
        self.table = table_name
        self.pool = self.database.pool
        self.timeout = self.database.timeout
        self.cache = {}

    @abstractmethod
    async def __async_init__(self) -> None:
        """
        This is asynchronous initialization function which
        will get automatically called by `Database` when
        the table is added. (Calling this method is handeled
        by the `_populate` function).
        """
        raise NotImplementedError

    async def _init(self) -> None:
        """
        This method calls `_populate` and `_make_cache`
        to make all the db tables and create the table cache.
        After that, `__async_init__` method is called which
        refers to top-level async initialization, if this
        method isn't defined, nothing will happen.

        This also makes sure that `columns` dictionary is
        defined properly in the top-level class..
        """
        if not hasattr(self, "columns") or not isinstance(self.columns, dict):
            raise RuntimeError(f"Table {self.__class__} doesn't have a `columns` dict defined properly.")

        await self._populate()
        await self._make_cache()
        with suppress(NotImplementedError):
            await self.__async_init__()

    async def _populate(self) -> None:
        """
        This method is used to create the initial table structure
        and define it's structure and columns.

        This method also calls `__async_init__` method on top level table
        (if there is one).
        """
        table_structure = ",\n".join(f"{column} {sql_details}" for column, sql_details in self.columns.items())
        populate_command = f"CREATE TABLE IF NOT EXISTS {self.table} (\n{table_structure}\n)"

        logger.trace(f"Populating {self.__class__}")
        async with self.pool.acquire(timeout=self.timeout) as db:
            await db.execute(populate_command)

    async def _make_cache(self) -> None:
        """
        Crate and populate basic caching model from top-level `self.caching`.

        This function creates `self.cache_columns` which stores the cached columns
        and their type together with `self.cache` which stores the actual cache.
        """
        if not hasattr(self, "caching") or not isinstance(self.caching, dict):
            logger.trace(f"Skipping defining cache for {self.__class__}, `caching` dict wasn't specified")
            return

        self.cache_columns = {}
        cache_key_type, self._cache_key = self.caching.pop("key")
        self.cache_columns[self._cache_key] = cache_key_type

        # Create cache model
        field_list = []
        for column, specification in self.caching.items():
            if isinstance(specification, tuple):
                val = (column, specification[0], field(default=specification[1]))
                _type = specification[0]
            elif specification is None:
                val = column
                _type = None
            else:
                val = (column, specification)
                _type = specification

            field_list.append(val)
            self.cache_columns[column] = _type

        self._cache_model = make_dataclass("Entry", field_list)

        # Create and populate the cache
        self.cache = defaultdict(self._cache_model)
        columns = list(self.columns.keys())

        entries = await self.db_get(columns)  # Get db entries to store
        for entry in entries:
            db_entry = {}
            for col_name, record in zip(columns, *iter(entry)):
                # Convert to specified type
                with suppress(IndexError, TypeError):
                    _type = self.cache_columns[col_name]
                    record = _type(record)
                db_entry[col_name] = record
            # Store the cache model into the cache
            key = db_entry.pop(self._cache_key)
            cache_entry = self._cache_model(**db_entry)
            self.cache[key] = cache_entry

    def cache_update(self, key: str, column: str, value: t.Any) -> None:
        """
        Update the stored cache value for `update_key` on `primary_value` to given `update_value`.
        """
        setattr(self.cache[key], column, value)

    def cache_get(self, key: str, column: str) -> t.Any:
        """
        Obtain the value of `attribute` stored in cache for `primary_value`
        """
        return getattr(self.cache[key], column)

    @classmethod
    def reference(cls) -> "DBTable":
        """
        This is a method which returns the running instance of given class.

        This works based on the singleton single instance model and it was
        added as a substitution for calling __init__ from the top level class
        directly, since that requires passing arguments which won't be used
        due to the single instance model, using the `reference` function
        allows you to retrieve this instance without the need of passing
        any additional arguments.

        It should be noted that using this will return the instance of the
        top-level class, but the editor will only see it as an instance of
        this class (`DBTable`) due to the return type being set to it.
        To circumvent this you should statically define the type of the
        variable which will be used to store this instance.
        """
        return cls._instance

    async def db_execute(self, sql: str, sql_args: t.Optional[list] = None) -> None:
        """
        This method serves as an abstraction layer
        from using context manager and executing the
        sql command directly from there.
        """
        if not sql_args:
            sql_args = []

        async with self.pool.acquire(timeout=self.timeout) as db:
            await db.execute(sql, *sql_args)

    async def db_fetchone(self, sql: str, sql_args: t.Optional[list] = None) -> asyncpg.Record:
        """
        This method serves as an abstraction layer
        from using context manager and fetching the
        sql query directly from there.
        """
        if not sql_args:
            sql_args = []

        async with self.pool.acquire(timeout=self.timeout) as db:
            return await db.fetchrow(sql, *sql_args)

    async def db_fetch(self, sql: str, sql_args: t.Optional[list] = None) -> t.List[asyncpg.Record]:
        """
        This method serves as an abstraction layer
        from using context manager and fetching the
        sql query directly from there.
        """
        if not sql_args:
            sql_args = []

        async with self.pool.acquire(timeout=self.timeout) as db:
            return await db.fetch(sql, *sql_args)

    async def db_get(
        self, columns: t.List[str], specification: t.Optional[str] = None, sql_args: t.Optional[list] = None
    ) -> t.Union[asyncpg.Record, t.List[asyncpg.Record]]:
        """
        This method serves as an abstraction layer
        from using SQL syntax in the top-level database
        table class, it runs the basic selection (get)
        query without needing to use SQL syntax at all.
        """
        sql = f"SELECT ({', '.join(columns)}) FROM {self.table}"
        if specification:
            sql += f" WHERE ({specification})"

        if len(columns) == 1:
            return await self.db_fetchone(sql, sql_args)
        return await self.db_fetch(sql, sql_args)

    async def db_set(self, columns: t.List[str], values: t.List[str]) -> None:
        """
        This method serves as an abstraction layer
        from using SQL syntax in the top-level database
        table class, it runs the basic insertion (set)
        command without needing to use SQL syntax at all.
        """
        sql_columns = ", ".join(columns)
        sql_values = ", ".join(f"${n + 1}" for n in range(len(values)))

        sql = f"""
        INSERT INTO {self.table} ({sql_columns})
        VALUES ({sql_values})
        """

        await self.db_execute(sql, values)

    async def db_set_return(
        self,
        columns: t.List[str],
        values: t.List[str],
        return_columns: t.List[str]
    ) -> t.Union[asyncpg.Record, t.List[asyncpg.Record]]:
        """
        This method serves as an abstraction layer
        from using SQL syntax in the top-level database
        table class, it runs the basic insertion (set)
        command and returns specified `return_column`
        without needing to use SQL syntax at all.
        """
        sql_columns = ", ".join(columns)
        sql_values = ", ".join(f"${n + 1}" for n in range(len(values)))
        sql_return_columns = ", ".join(return_columns)

        sql = f"""
        INSERT INTO {self.table} ({sql_columns})
        VALUES ({sql_values})
        RETURNING ({sql_return_columns})
        """

        if len(return_columns) == 1:
            return await self.db_fetchone(sql, values)
        return await self.db_fetch(sql, values)

    async def db_upsert(self, columns: t.List[str], values: t.List[str], conflict_columns: t.List[str]) -> None:
        """
        This method serves as an abstraction layer
        from using SQL syntax in the top-level database
        table class, it runs the basic insert/update (upsert)
        command without needing to use SQL syntax at all.
        """
        sql_columns = ", ".join(columns)
        sql_values = ", ".join(f"${n + 1}" for n in range(len(values)))
        sql_conflict_columns = ", ".join(conflict_columns)

        sql_update = ""
        for index, column in enumerate(columns):
            if column not in conflict_columns:
                sql_update += f"{column}=${index + 1}"

        sql = f"""
        INSERT INTO {self.table} ({sql_columns})
        VALUES ({sql_values})
        ON CONFLICT ({sql_conflict_columns}) DO
        UPDATE SET {sql_update}
        """

        await self.db_execute(sql, values)


class Database(metaclass=Singleton):
    """
    This is the main connection class with the postgres database.

    This class is here to ensure the ease of connecting and
    disconnecting from the database and loading the top-level
    database table classes.
    """
    def __init__(self, db_parameters: dict, timeout: int = 5):
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
        """
        Connect to the database using the `self.db_parameters`
        provided in the `__init__` method.

        Store this connection in `self.pool` attribute
        """
        logger.debug("Connecting to the database")
        try:
            self.pool = await asyncpg.create_pool(**self.db_parameters)
        except (asyncpg.exceptions.PostgresError, ConnectionRefusedError):
            logger.error("Unable to connect to the database")
            return False

        return True

    async def disconnect(self) -> None:
        """Close the database pool connection."""
        logger.debug("Closing connection to the database")
        await self.pool.close()

    async def load_tables(self, tables: t.List[str], bot: "Bot") -> None:
        """
        Load on all given `tables`.

        This function imports every table in `tables` and awaits
        the `load` coroutine which initiates the top-level
        database table class and calls `self.load_table`.
        """
        for table in tables:
            logger.trace(f"Adding {table} table")
            module = import_module(table)
            if not hasattr(module, "load"):
                logger.error(f"Unable to load table: {table} (this: {__name__} module: {module}), it doesn't have the async `load` function set up")
                return
            await module.load(bot, self)

    async def add_table(self, table: DBTable) -> None:
        """
        Add the `table` into the `self.tables` set and
        execute it's `_populate` function.

        In case the `table` is already added, log a warning
        and don't add it into the table. The `_populate` function
        won't be called either.
        """
        if table in self.tables:
            logger.warning(f"Tried to add already added table ({table.__class__}), skipping.")
            return
        if not isinstance(table, DBTable):
            raise TypeError("`table` argument must be an instance of `DBTable`")

        self.tables.add(table)
        await table._init()

    async def remove_table(self, table: "DBTable") -> None:
        """
        Remove the table from `self.tables`.

        This also reset's the `table`s unique singleton instance.
        """
        if table not in self.tables:
            logger.warning(f"Tried to remove unknown table ({table.__class__})")

        logger.trace(f"Removing {table.__class__}")
        self.tables.remove(table)
        table._instance = None

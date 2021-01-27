import os
import pathlib
import typing as t

from loguru import logger
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


def load_tables() -> t.List[Base]:
    """
    Import all database tables in order to load them
    into the `Base` metadata, so that they can be initialized.
    """
    loaded_modules = []

    # Auto database modules discovery
    database_dir = pathlib.Path(os.getcwd(), "bot", "database")
    db_modules = [f for f in os.listdir(database_dir) if pathlib.Path(database_dir, f).is_file() and f.endswith(".py")]

    # Load found modules
    for db_module in db_modules:
        db_module = db_module.replace(".py", "")
        import_path = f"bot.database.{db_module}"
        try:
            loaded_modules.append(__import__(import_path))
        except ImportError as e:
            logger.error(f"Unable to load database: {import_path} --> {e}")

    return loaded_modules


async def upsert(session: AsyncSession, model: Base, conflict_columns: list, values: dict) -> None:
    """
    SQLAlchemy lacks postgres specific upsert function, this is
    it's implementation to avoid code repetition in the database models.
    """
    table = model.__table__
    stmt = postgresql.insert(table)
    affected_columns = {
        col.name: col for col in stmt.excluded
        if col.name in values and col.name not in conflict_columns
    }

    if not affected_columns:
        raise ValueError("Couldn't find any columns to update.")

    stmt = stmt.on_conflict_do_update(
        index_elements=conflict_columns,
        set_=affected_columns
    )

    await session.execute(stmt, values)

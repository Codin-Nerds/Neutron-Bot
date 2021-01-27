from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


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

import typing as t

from discord import Guild, Member, Role, TextChannel, User
from loguru import logger
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base

from bot.core.autoload import DATABASES, readable_name


Base = declarative_base()


def load_tables() -> t.List[Base]:
    """
    Import all database tables in order to load them
    into the `Base` metadata, so that they can be initialized.
    """
    loaded_modules = []

    # Load found modules
    for db_module_import_path in DATABASES:
        try:
            loaded_modules.append(__import__(db_module_import_path))
        except ImportError as e:
            logger.error(f"Unable to load database: {readable_name(db_module_import_path)} --> {e}")

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


# region: Common getters for tables

def get_str_guild(guild: t.Union[str, int, Guild]) -> str:
    """Make sure `guild` parameter is string."""
    if isinstance(guild, Guild):
        guild = str(guild.id)
    if isinstance(guild, int):
        guild = str(guild)
    return guild


def get_str_role(role: t.Union[str, int, Role]) -> str:
    """Make sure `role` parameter is string."""
    if isinstance(role, Role):
        role = str(role.id)
    if isinstance(role, int):
        role = str(role)
    return role


def get_str_channel(channel: t.Union[str, int, TextChannel]) -> str:
    """Make sure `channel` parameter is string."""
    if isinstance(channel, TextChannel):
        channel = str(channel.id)
    if isinstance(channel, int):
        channel = str(channel)
    return channel


def get_str_user(member: t.Union[str, int, Member, User]) -> str:
    """Make sure `member` parameter is string."""
    if isinstance(member, (Member, User)):
        member = str(member.id)
    if isinstance(member, int):
        member = str(member)
    return member

# endregion

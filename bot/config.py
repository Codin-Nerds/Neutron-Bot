import os
from enum import Enum


COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ">>")

DEV_MODE = True

# Aviable types of strikes
STRIKE_TYPES = [
    "ban", "kick", "mute", "note", "custom",
    "automod-ban", "automod-kick", "automod-mute", "automod-note",
]

# Database
DATABASE = {
    "host": os.getenv("DATABASE_HOST", "127.0.0.1"),
    "database": os.getenv("DATABASE_NAME", "bot"),
    "user": os.getenv("DATABASE_USER", "bot"),
    "password": os.getenv("DATABASE_PASSWORD", "bot"),
}
DATABASE_ENGINE_STRING = f"postgresql+asyncpg://{DATABASE['user']}:{DATABASE['password']}@{DATABASE['host']}/{DATABASE['database']}"


class Event(Enum):
    """
    Used to identify specific event for bot.cogs.logging.mod_log.
    This isn't in sync with all discord.py real events, it is here
    to hold a unique identifier for each event
    """
    member_ban = "member_ban"
    member_unban = "member_unban"
    member_kick = "member_kick"
    member_mute = "member_mute"

    member_join = "member_join"
    member_remove = "member_remove"
    member_update = "member_update"
    user_update = "user_update"

    message_edit = "message_edit"
    message_delete = "message_delete"

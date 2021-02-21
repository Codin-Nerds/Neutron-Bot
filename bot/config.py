import os
from enum import Enum


# Developer Mode Settings:
DEV_MODE = True

# Ownership settings:
creator = "The Codin Nerds Team"
devs = [711194921683648523, 306876636526280705]

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

# Prefix Settings
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ">>")


class Event(Enum):
    """
    Used to identify specific event for bot.cogs.logging.mod_log.
    This isn't in sync with all discord.py real events, it is here
    to hold a unique identifier for each event
    """
    member_kick = "member_kick"
    member_ban = "member_ban"
    member_unban = "member_unban"

    member_join = "member_join"
    member_remove = "member_remove"
    member_update = "member_update"

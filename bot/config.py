import os
from enum import Enum


TOKEN = os.getenv("BOT_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ">>")

# Debug/Development mode
# If not defined or defined as false, set to False, otherwise, set to True
DEBUG = "DEBUG" in os.environ and os.environ["DEBUG"].lower() != "false"

# Database
DATABASE = {
    "host": os.getenv("DATABASE_HOST", "127.0.0.1"),
    "database": os.getenv("DATABASE_NAME", "bot"),
    "user": os.getenv("DATABASE_USER", "bot"),
    "password": os.getenv("DATABASE_PASSWORD", "bot"),
}
DATABASE_ENGINE_STRING = f"postgresql+asyncpg://{DATABASE['user']}:{DATABASE['password']}@{DATABASE['host']}/{DATABASE['database']}"


class StrikeType(Enum):
    """Lists all available types for a strike."""
    ban = "ban"
    kick = "kick"
    mute = "mute"
    note = "note"
    custom = "custom"
    automod_ban = "automod_ban"
    automod_kick = "automod_kick"
    automod_mute = "automod_mute"
    automod_note = "automod_note"


class Event(Enum):
    """
    Used to identify specific event for bot.cogs.logging.mod_log.
    This isn't in sync with all discord.py real events, it is here
    to hold a unique identifier for each event.
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

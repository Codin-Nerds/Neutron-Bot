import os

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
    "database": os.getenv("DATABASE_NAME"),
    "user": os.getenv("DATABASE_USER"),
    "password": os.getenv("DATABASE_PASSWORD"),
}
DATABASE_ENGINE_STRING = f"postgresql+asyncpg://{DATABASE['user']}:{DATABASE['password']}@{DATABASE['host']}/{DATABASE['database']}"

# Prefix Settings
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ">>")

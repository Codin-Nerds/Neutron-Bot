# Imports
import os

# Developer Mode Settings:
DEV_MODE = True

# Database
DATABASE = {
    "host": os.getenv("DATABASE_HOST", "127.0.0.1"),
    "database": os.getenv("DATABASE_NAME"),
    "user": os.getenv("DATABASE_USER"),
    "password": os.getenv("DATABASE_PASSWORD"),
    "min_size": int(os.getenv("POOL_MIN", "20")),
    "max_size": int(os.getenv("POOL_MAX", "100")),
}

# Prefix Settings
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ">>")

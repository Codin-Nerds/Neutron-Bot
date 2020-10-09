import os

from discord import Game

from bot import config
from bot.core.bot import Bot

TOKEN = os.getenv("BOT_TOKEN")
PREFIX = config.COMMAND_PREFIX

extensions = [
    "bot.cogs.moderation.lock",
    "bot.cogs.sudo",
    "bot.cogs.embeds"
]
db_tables = [
    "bot.database.roles"
]

bot = Bot(
    extensions, db_tables,
    command_prefix=PREFIX,
    activity=Game(name=f"Ping me using {PREFIX}help"),
    case_insensitive=True,
)


if __name__ == "__main__":
    bot.run(TOKEN)

import os

from discord import Game

from bot import config
from bot.core.bot import Bot

TOKEN = os.getenv("BOT_TOKEN")
PREFIX = config.COMMAND_PREFIX

extensions = [
    "bot.cogs.error_handler",
    "bot.cogs.help",
    "bot.cogs.sudo",
    "bot.cogs.moderation.lock",
    "bot.cogs.moderation.slowmode",
    "bot.cogs.setup.roles",
    "bot.cogs.setup.permissions",
    "bot.cogs.embeds",
]
db_tables = [
    "bot.database.roles",
    "bot.database.permissions",
]

bot = Bot(
    extensions, db_tables,
    command_prefix=PREFIX,
    activity=Game(name=f"Ping me using {PREFIX}help"),
    case_insensitive=True,
)


if __name__ == "__main__":
    bot.run(TOKEN)

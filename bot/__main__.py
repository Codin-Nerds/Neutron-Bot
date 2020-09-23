import os

from bot import config
from bot.core.bot import Bot

from discord import Game


TOKEN = os.getenv("BOT_TOKEN")
PREFIX = config.COMMAND_PREFIX

extensions = [
    "bot.cogs.fun",

    "bot.cogs.games",
    "bot.cogs.gamestats",

    "bot.cogs.info",

    "bot.cogs.moderation",

    "bot.cogs.owner",
]


bot = Bot(
    extensions,
    command_prefix=PREFIX,
    activity=Game(name=f"Ping me using {PREFIX}help"),
    case_insensitive=True,
)


if __name__ == "__main__":
    bot.run(TOKEN)

import os

from discord import Game

from bot import config
from bot.core.bot import Bot

TOKEN = os.getenv("BOT_TOKEN")
PREFIX = config.COMMAND_PREFIX

bot = Bot(
    config.extensions,
    command_prefix=PREFIX,
    activity=Game(name=f"Ping me using {PREFIX}help"),
    case_insensitive=True,
)


if __name__ == "__main__":
    bot.run(TOKEN)

import os

from bot import config
from bot.core.bot import Bot

from bot.core.exceptions import TokenNotFoundError

from discord import Game

import colorama


TOKEN = os.getenv("BOT_TOKEN")
PREFIX = config.COMMAND_PREFIX

extensions = [
    "bot.cogs.common",

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
    if TOKEN:
        bot.run(TOKEN)
    else:
        colorama.init(autoreset=True)

        raise TokenNotFoundError(
            f"""
            {colorama.Fore.RED}
            Wupsy! Token not found
            Are you running this file through pipenv and
            is there a .env file containing a BOT_TOKEN key
            in your current working directory?
            """
        )

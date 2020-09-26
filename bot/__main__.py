import os

from discord import Game

from bot import config
from bot.core.bot import Bot

TOKEN = os.getenv("BOT_TOKEN")
PREFIX = config.COMMAND_PREFIX

extensions = [
    # "bot.cogs.example",
]


bot = Bot(
    extensions,
    command_prefix=PREFIX,
    activity=Game(name=f"Ping me using {PREFIX}help"),
    case_insensitive=True,
)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            """
            Bot token missing, make sure your `.env` file contains
            BOT_TOKEN key and you're using pipenv to set these.
            """
        )

    bot.run(TOKEN)

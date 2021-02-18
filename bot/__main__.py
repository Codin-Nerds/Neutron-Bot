import os

from discord import Game, Intents

from bot import config
from bot.core.bot import Bot

TOKEN = os.getenv("BOT_TOKEN")
PREFIX = config.COMMAND_PREFIX

intents = Intents.default()
intents.guilds = True
intents.members = True  # Requires discord app permission

bot = Bot(
    command_prefix=PREFIX,
    activity=Game(name=f"Ping me using {PREFIX}help"),
    case_insensitive=True,
    intents=intents
)


if __name__ == "__main__":
    bot.run(TOKEN)

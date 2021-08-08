from discord import Game, Intents

from bot import config
from bot.core.bot import Bot

intents = Intents.default()
intents.guilds = True
intents.bans = True
intents.messages = True
intents.members = True  # Requires discord app permission

bot = Bot(
    command_prefix=config.COMMAND_PREFIX,
    activity=Game(name=f"Ping me using {config.COMMAND_PREFIX}help"),
    case_insensitive=True,
    intents=intents
)


if __name__ == "__main__":
    bot.run(config.TOKEN)  # pragma: no cover

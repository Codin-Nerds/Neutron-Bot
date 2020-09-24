from discord.ext.commands import Cog

from bot.core.bot import Bot


class Music(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot


def setup(bot: Bot) -> None:
    bot.add_cog(Music(bot))

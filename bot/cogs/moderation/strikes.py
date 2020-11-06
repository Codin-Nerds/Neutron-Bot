from discord.ext.commands import Cog, Context

from bot.core.bot import Bot
from bot.database.strikes import Strikes as StrikesDB


class Strikes(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.strikes_db: StrikesDB = StrikesDB.reference()

    async def cog_check(self, ctx: Context) -> bool:
        if ctx.author.permissions_in(ctx.channel).administrator:
            return True

        return False


def setup(bot: Bot) -> None:
    bot.add_cog(Strikes(bot))

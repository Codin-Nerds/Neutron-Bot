import typing as t
from discord.ext.commands import Cog, Context, group
from discord.ext.commands.errors import BadArgument

from bot.config import STRIKE_TYPES
from bot.core.bot import Bot
from bot.core.converters import ProcessedUser
from bot.database.strikes import Strikes as StrikesDB


class Strikes(Cog):
    """
    Since this cog interracts with strikes database entries directly,
    it is limited to administrators. This doesn't mean others won't
    have permissions to add strikes, but it will be done with other
    commands, such as `ban`, `kick`, etc., these commands will be used
    in different cogs, and the strikes will be added automatically.
    This is manual way for direct adjustment, creation or deletion of strikes.
    """
    def __init__(self, bot: Bot):
        self.bot = bot
        self.strikes_db: StrikesDB = StrikesDB.reference()

    @group(invoke_without_command=True, name="strike", aliases=["strikes", "infraction", "infractions"])
    async def strike_group(self, ctx: Context) -> None:
        """Commands for configuring the Embed messages."""
        await ctx.send_help(ctx.command)

    @strike_group.command()
    async def add(self, ctx: Context, user: ProcessedUser, strike_type: str, *, reason: t.Optional[str]) -> None:
        """Add a new strike to given `user`"""
        if strike_type not in STRIKE_TYPES:
            raise BadArgument(f"Invalid strike type, possible types are: {', '.join(STRIKE_TYPES)}")

        await self.strikes_db.add_strike(ctx.guild, ctx.author, user, strike_type, reason)
        await ctx.send(f"✅ {strike_type} strike applied to {user} for: {reason}")

    async def cog_check(self, ctx: Context) -> bool:
        """
        Only allow users with administrator permission to use these function.

        For details about why is this cog limited for admins only, check the cog description.
        """
        if ctx.author.permissions_in(ctx.channel).administrator:
            return True

        return False


def setup(bot: Bot) -> None:
    bot.add_cog(Strikes(bot))

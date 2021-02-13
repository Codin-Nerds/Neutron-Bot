import typing as t

from discord.ext.commands import Cog, Context, group
from discord.ext.commands.errors import BadArgument, MissingPermissions
from sqlalchemy.exc import NoResultFound

from bot.config import STRIKE_TYPES
from bot.core.bot import Bot
from bot.database.strikes import Strikes as StrikesDB
from bot.utils.converters import ProcessedUser


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

    @group(invoke_without_command=True, name="strike", aliases=["strikes", "infraction", "infractions"])
    async def strike_group(self, ctx: Context) -> None:
        """
        Commands for configuring the strike messages.

        Note: Strike manipulation is usually a bad idea, if you want to
        add a strike to the user, you can use commands made for it.
        Using this will manually add the strike, without invoking the action
        which naturally comes with it (such as ban, kick, etc.).
        """
        await ctx.send_help(ctx.command)

    @strike_group.command(aliases=["create"])
    async def add(self, ctx: Context, user: ProcessedUser, strike_type: str, *, reason: t.Optional[str] = None) -> None:
        """Add a new strike to given `user`"""
        if strike_type not in STRIKE_TYPES:
            raise BadArgument(f"Invalid strike type, possible types are: `{', '.join(STRIKE_TYPES)}`")

        strike_id = await StrikesDB.set_strike(self.bot.db_session, ctx.guild, user, ctx.author, strike_type, reason)
        await ctx.send(f"✅ {strike_type} strike (ID: `{strike_id}`) applied to {user.mention}, reason: `{reason}`")

    @strike_group.command(aliases=["del"])
    async def remove(self, ctx: Context, strike_id: int) -> None:
        try:
            await StrikesDB.remove_strike(self.bot.db_session, ctx.guild, strike_id)
        except NoResultFound:
            await ctx.send(f"❌ Strike with ID `{strike_id}` does not exist.")
        else:
            await ctx.send(f"✅ Strike with ID `{strike_id}` has been removed.")

    async def cog_check(self, ctx: Context) -> bool:
        """
        Only allow users with administrator permission to use these function.

        For details about why is this cog limited for admins only, check the cog description.
        """
        if ctx.author.permissions_in(ctx.channel).administrator:
            return True

        raise MissingPermissions("Only members with administrator rights can use this command.")


def setup(bot: Bot) -> None:
    bot.add_cog(Strikes(bot))

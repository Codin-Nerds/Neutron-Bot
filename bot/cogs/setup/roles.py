from discord.ext.commands import Cog, Context, RoleConverter, command

from bot.core.bot import Bot
from bot.database.roles import Roles


class RolesSetup(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.roles_db: Roles = Roles.reference()

    @command(aliases=["defaultrole"])
    async def default_role(self, ctx: Context, role: RoleConverter) -> None:
        """Setup default role."""
        await self.roles_db.set_default_role(ctx.guild, role)

    @command(aliases=["staffrole"])
    async def staff_role(self, ctx: Context, role: RoleConverter) -> None:
        """Handle the server setup."""
        await self.roles_db.set_staff_role(ctx.guild, role)

    @command(aliases=["mutedrole"])
    async def muted_role(self, ctx: Context, role: RoleConverter) -> None:
        """Handle the server setup."""
        await self.roles_db.set_muted_role(ctx.guild, role)


def setup(bot: Bot) -> None:
    bot.add_cog(RolesSetup(bot))

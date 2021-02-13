import textwrap
import typing as t

from discord import Embed, Role
from discord.ext.commands import Cog, Context, RoleConverter, command
from discord.ext.commands.errors import MissingPermissions

from bot.core.bot import Bot
from bot.database.roles import Roles


class RolesSetup(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @command(aliases=["defaultrole"])
    async def default_role(self, ctx: Context, role: RoleConverter) -> None:
        """Setup default role."""
        await Roles.set_role(self.bot.db_session, "default", ctx.guild, role)
        await ctx.send(":white_check_mark: Role updated.")

    @command(aliases=["staffrole"])
    async def staff_role(self, ctx: Context, role: RoleConverter) -> None:
        """Setup the staff role."""
        await Roles.set_role(self.bot.db_session, "staff", ctx.guild, role)
        await ctx.send(":white_check_mark: Role updated.")

    @command(aliases=["mutedrole"])
    async def muted_role(self, ctx: Context, role: RoleConverter) -> None:
        """Setup the muted role."""
        await Roles.set_role(self.bot.db_session, "muted", ctx.guild, role)
        await ctx.send(":white_check_mark: Role updated.")

    @command(aliases=["showroles"])
    async def show_roles(self, ctx: Context) -> None:
        """Show configured roles in the server."""
        roles = await Roles.get_roles(self.bot.db_session, ctx.guild)
        default = ctx.guild.get_role(roles["default_role"])
        staff = ctx.guild.get_role(roles["staff_role"])
        muted = ctx.guild.get_role(roles["muted_role"])

        if isinstance(default, Role):
            default = default.mention
        if isinstance(staff, Role):
            staff = staff.mention
        if isinstance(muted, Role):
            muted = muted.mention

        embed = Embed(
            title="Configured role settings",
            description=textwrap.dedent(
                f"""
                Default role: {default}
                Staff role: {staff}
                Muted role: {muted}
                """
            )
        )

        await ctx.send(embed=embed)

    async def cog_check(self, ctx: Context) -> t.Optional[bool]:
        """Only allow users with administrator permission to use these functions."""
        if ctx.author.guild_permissions.administrator:
            return True

        raise MissingPermissions("Only members with administrator rights can use this command.")


def setup(bot: Bot) -> None:
    bot.add_cog(RolesSetup(bot))

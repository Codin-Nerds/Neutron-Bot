import textwrap

from discord import Embed, Role
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
        await ctx.send(":white_check_mark: Role updated.")

    @command(aliases=["staffrole"])
    async def staff_role(self, ctx: Context, role: RoleConverter) -> None:
        """Setup the staff role."""
        await self.roles_db.set_staff_role(ctx.guild, role)
        await ctx.send(":white_check_mark: Role updated.")

    @command(aliases=["mutedrole"])
    async def muted_role(self, ctx: Context, role: RoleConverter) -> None:
        """Setup the muted role."""
        await self.roles_db.set_muted_role(ctx.guild, role)
        await ctx.send(":white_check_mark: Role updated.")

    @command(aliases=["showroles"])
    async def show_roles(self, ctx: Context) -> None:
        """Show configured roles in the server."""
        default = ctx.guild.get_role(self.roles_db.get_default_role(ctx.guild))
        staff = ctx.guild.get_role(self.roles_db.get_staff_role(ctx.guild))
        muted = ctx.guild.get_role(self.roles_db.get_muted_role(ctx.guild))

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


def setup(bot: Bot) -> None:
    bot.add_cog(RolesSetup(bot))

import textwrap

from discord import Embed
from discord.ext.commands import Cog, Context, RoleConverter, command

from bot.core.bot import Bot
from bot.core.converters import Duration
from bot.database.permissions import Permissions
from bot.utils.time import stringify_duration


class PermissionsSetup(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.permissions_db: Permissions = Permissions.reference()

    @command(aliases=["bantime"])
    async def ban_time(self, ctx: Context, role: RoleConverter, duration: Duration) -> None:
        """
        Set maximum time users with specified role can ban users for.

        If user have multiple roles with different ban times,
        the ban time for role higher in the hierarchy will be preferred.
        """
        await self.permissions_db.set_bantime(ctx.guild, role, duration)
        await ctx.send(":white_check_mark: Permissions updated.")

    @command(aliases=["mutetime"])
    async def mute_time(self, ctx: Context, role: RoleConverter, duration: Duration) -> None:
        """
        Set maximum time users with specified role can mute users for.

        If user have multiple roles with different mute times,
        the mute time for role higher in the hierarchy will be preferred.
        """
        await self.permissions_db.set_mutetime(ctx.guild, role, duration)
        await ctx.send(":white_check_mark: Permissions updated.")

    @command(aliases=["locktime"])
    async def lock_time(self, ctx: Context, role: RoleConverter, duration: Duration) -> None:
        """
        Set maximum time users with specified role can lock channels for.

        If user have multiple roles with different lock times,
        the lock time for role higher in the hierarchy will be preferred.
        """
        await self.permissions_db.set_locktime(ctx.guild, role, duration)
        await ctx.send(":white_check_mark: Permissions updated.")

    @command(aliases=["showpermissions"])
    async def show_permissions(self, ctx: Context, role: RoleConverter) -> None:
        """Show configured role permissions for the given `role`"""
        ban_time = await self.permissions_db.get_bantime(ctx.guild, role)
        mute_time = await self.permissions_db.get_mutetime(ctx.guild, role)
        lock_time = await self.permissions_db.get_locktime(ctx.guild, role)

        if ban_time:
            ban_time = stringify_duration(ban_time)
        if mute_time:
            mute_time = stringify_duration(mute_time)
        if lock_time:
            lock_time = stringify_duration(lock_time)

        embed = Embed(
            description=textwrap.dedent(
                f"""
                **Permissions for {role.mention} role**

                Maximum ban time: `{ban_time}`
                Maximum mute time: `{mute_time}`
                Maximum Lock time: `{lock_time}`
                """
            )
        )

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(PermissionsSetup(bot))

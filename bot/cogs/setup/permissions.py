import textwrap
import typing as t

from discord import Embed
from discord.ext.commands import Cog, Context, RoleConverter, command
from discord.ext.commands.errors import MissingPermissions

from bot.core.bot import Bot
from bot.core.converters import Duration
from bot.database.permissions import Permissions
from bot.utils.time import stringify_duration


class PermissionsSetup(Cog):
    """
    This cog is here to provide initial setup of log channels for given guild.
    After that, there usually isn't a use for it anymore, unless that channel is changed.
    """
    def __init__(self, bot: Bot):
        self.bot = bot

    @command(aliases=["bantime"])
    async def ban_time(self, ctx: Context, role: RoleConverter, duration: Duration) -> None:
        """
        Set maximum time users with specified role can ban users for.

        If user have multiple roles with different ban times,
        the ban time for role higher in the hierarchy will be preferred.
        """
        await Permissions.set_role_permission(self.bot.db_session, "ban", ctx.guild, role, duration)
        await ctx.send(":white_check_mark: Permissions updated.")

    @command(aliases=["mutetime"])
    async def mute_time(self, ctx: Context, role: RoleConverter, duration: Duration) -> None:
        """
        Set maximum time users with specified role can mute users for.

        If user have multiple roles with different mute times,
        the mute time for role higher in the hierarchy will be preferred.
        """
        await Permissions.set_role_permission(self.bot.db_session, "mute", ctx.guild, role, duration)
        await ctx.send(":white_check_mark: Permissions updated.")

    @command(aliases=["locktime"])
    async def lock_time(self, ctx: Context, role: RoleConverter, duration: Duration) -> None:
        """
        Set maximum time users with specified role can lock channels for.

        If user have multiple roles with different lock times,
        the lock time for role higher in the hierarchy will be preferred.
        """
        await Permissions.set_role_permission(self.bot.db_session, "lock", ctx.guild, role, duration)
        await ctx.send(":white_check_mark: Permissions updated.")

    @command(aliases=["showpermissions"])
    async def show_permissions(self, ctx: Context, role: RoleConverter) -> None:
        """Show configured role permissions for the given `role`"""
        permissions = await Permissions.get_permissions(self.bot.db_session, ctx.guild, role)

        ban_time = stringify_duration(permissions["ban_time"]) if permissions["ban_time"] else None
        mute_time = stringify_duration(permissions["mute_time"]) if permissions["mute_time"] else None
        lock_time = stringify_duration(permissions["lock_time"]) if permissions["lock_time"] else None

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

    async def cog_check(self, ctx: Context) -> t.Optional[bool]:
        """Only allow users with administrator permission to use these functions."""
        if ctx.author.guild_permissions.administrator:
            return True

        raise MissingPermissions("Only members with administrator rights can use this command.")


def setup(bot: Bot) -> None:
    bot.add_cog(PermissionsSetup(bot))

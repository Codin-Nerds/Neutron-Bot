import typing as t

from discord import Color, Embed
from discord.ext.commands import Cog, Context, RoleConverter, group
from discord.ext.commands.errors import MissingPermissions

from bot.core.bot import Bot
from bot.database.permissions import Permissions
from bot.utils.converters import Duration
from bot.utils.time import stringify_duration


class PermissionsSetup(Cog):
    """
    This cog is here to provide initial setup of log channels for given guild.
    After that, there usually isn't a use for it anymore, unless that channel is changed.
    """
    def __init__(self, bot: Bot):
        self.bot = bot

    @group(invoke_without_command=True, name="permissions", aliases=["perm", "perms"])
    async def permissions_group(self, ctx: Context, permission_type: str, role: RoleConverter, duration: Duration) -> None:
        """Commands for configuring the role permissions."""
        try:
            await Permissions.set_role_permission(self.bot.db_session, permission_type, ctx.guild, role, duration)
        except ValueError:
            await ctx.send(f":x: Invalid logging type, types: `{', '.join(Permissions.valid_time_types)}`")
            return
        await ctx.send(":white_check_mark: Permissions updated.")

    @permissions_group.command(aliases=["info", "status"])
    async def show(self, ctx: Context, role: RoleConverter) -> None:
        """Show configured log channels."""
        obtained_times = await Permissions.get_permissions(self.bot.db_session, ctx.guild, role)

        description_lines = []
        for time_type in Permissions.valid_time_types:

            time = obtained_times.get(time_type, None)
            readable_time = stringify_duration(time) if time is not None else '<not configured>'

            readable_time_type = time_type.replace("_time", "")
            description_lines.append(f"Maximum {readable_time_type} time: {readable_time}")

        embed = Embed(
            title=f"Permissions for {role} role",
            description="\n".join(description_lines),
            color=Color.blue()
        )

        await ctx.send(embed=embed)

    async def cog_check(self, ctx: Context) -> t.Optional[bool]:
        """Only allow users with administrator permission to use these functions."""
        if ctx.author.guild_permissions.administrator:
            return True

        raise MissingPermissions("Only members with administrator rights can use this command.")


def setup(bot: Bot) -> None:
    bot.add_cog(PermissionsSetup(bot))

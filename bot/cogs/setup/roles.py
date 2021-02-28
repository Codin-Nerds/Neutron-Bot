import typing as t

from discord import Color, Embed
from discord.ext.commands import Cog, Context, group
from discord.ext.commands.converter import RoleConverter
from discord.ext.commands.errors import MissingPermissions

from bot.core.bot import Bot
from bot.database.roles import Roles


class RolesSetup(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @group(invoke_without_command=True, name="roles", aliases=["role"])
    async def roles_group(self, ctx: Context, role_type: str, role: RoleConverter) -> None:
        """Commands for configuring the server roles."""
        try:
            await Roles.set_role(self.bot.db_engine, role_type, ctx.guild, role)
        except ValueError:
            await ctx.send(f":x: Invalid role type, types: `{', '.join(Roles.valid_role_types)}`")
            return
        await ctx.send(":white_check_mark: Permissions updated.")

    @roles_group.command(aliases=["info", "status"])
    async def show(self, ctx: Context) -> None:
        """Show configured log channels."""
        obtained_roles = await Roles.get_roles(self.bot.db_engine, ctx.guild)

        description_lines = []
        for role_type in Roles.valid_role_types:

            role_id = obtained_roles.get(role_type, None)
            role = ctx.guild.get_role(role_id)
            readable_role = role.mention if role is not None else '<not configured>'

            readable_role_type = role_type.replace("_role", "").capitalize()
            description_lines.append(f"{readable_role_type} role: {readable_role}")

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
    bot.add_cog(RolesSetup(bot))

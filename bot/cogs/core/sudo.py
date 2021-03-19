import platform
import textwrap
import typing as t
from datetime import datetime

from discord import Color, Embed
from discord import __version__ as discord_version
from discord.ext.commands import Cog, Context, NotOwner, group
from discord.ext.commands.errors import ExtensionAlreadyLoaded, ExtensionNotLoaded

from bot.core.autoload import readable_name as readable_extension_name
from bot.core.bot import Bot
from bot.utils.converters import ValidExtension
from bot.utils.time import stringify_timedelta


class Sudo(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @group(invoke_without_command=True, hidden=True)
    async def sudo(self, ctx: Context) -> None:
        """Administrative information."""
        await ctx.send_help(ctx.command)

    @sudo.command()
    async def load(self, ctx: Context, extension: ValidExtension) -> None:
        try:
            self.bot.load_extension(extension)
        except ExtensionAlreadyLoaded:
            await ctx.send("❌ Extension is already loaded")
            return
        await ctx.send(f"✅ Extension {readable_extension_name(extension)} loaded")

    @sudo.command()
    async def unload(self, ctx: Context, extension: ValidExtension) -> None:
        try:
            self.bot.unload_extension(extension)
        except ExtensionNotLoaded:
            await ctx.send("❌ Extension is not loaded")
            return
        await ctx.send(f"✅ Extension {readable_extension_name(extension)} unloaded")

    @sudo.command()
    async def reload(self, ctx: Context, extension: ValidExtension) -> None:
        try:
            self.bot.unload_extension(extension)
        except ExtensionNotLoaded:
            pass
        self.bot.load_extension(extension)
        await ctx.send(f"✅ Extension {readable_extension_name(extension)} reloaded")

    @sudo.command()
    async def stats(self, ctx: Context) -> None:
        """Show full bot stats."""
        general = textwrap.dedent(
            f"""
            • Servers: **`{len(self.bot.guilds)}`**
            • Commands: **`{len(self.bot.commands)}`**
            • Members: **`{len(set(self.bot.get_all_members()))}`**
            • Uptime: **{stringify_timedelta(datetime.utcnow() - self.bot.start_time)}**
            """
        )
        system = textwrap.dedent(
            f"""
            • Python: **`{platform.python_version()} with {platform.python_implementation()}`**
            • discord.py: **`{discord_version}`**
            """
        )

        embed = Embed(title="BOT STATISTICS", color=Color.blue())
        embed.add_field(name="**❯❯ General**", value=general, inline=True)
        embed.add_field(name="**❯❯ System**", value=system, inline=True)

        embed.set_author(name=f"{self.bot.user.name}'s Stats", icon_url=self.bot.user.avatar_url)
        embed.set_footer(text="Made by The Codin' Nerds Team.")

        await ctx.send(embed=embed)

    async def cog_check(self, ctx: Context) -> t.Optional[bool]:
        """Only the bot owners can use this."""
        if await self.bot.is_owner(ctx.author):
            return True

        raise NotOwner


def setup(bot: Bot) -> None:
    bot.add_cog(Sudo(bot))

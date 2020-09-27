import os
import platform
import textwrap
import time
import traceback
import typing as t
from datetime import datetime

from discord import Color, DiscordException, Embed
from discord import __version__ as discord_version
from discord.ext.commands import Cog, Context, group


from bot.core.bot import Bot
from bot import config


def get_uptime(self) -> str:
    """Get formatted bot's uptime."""
    now = datetime.utcnow()
    delta = now - self.bot.start_time

    hours, rem = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(rem, 60)
    days, hours = divmod(hours, 24)

    if days:
        formatted = f"`{days}` days, `{hours}` hr, `{minutes}` mins, and `{seconds}` secs"
    else:
        formatted = f"`{hours}` hr, `{minutes}` mins, and `{seconds}` secs"

    return formatted


class Owner(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @group(hidden=True)
    async def sudo(self, ctx: Context) -> None:
        """Administrative information."""
        pass

    @sudo.command()
    async def shutdown(self, ctx: Context) -> None:
        """Turn the bot off."""
        if ctx.author.id in config.devs:
            await ctx.message.add_reaction("✅")
            await self.bot.logout()

    @sudo.command()
    async def restart(self, ctx: Context) -> None:
        """Restart the bot."""
        if ctx.author.id in config.devs:
            await ctx.message.add_reaction("✅")
            await self.bot.logout()
            time.sleep(1)
            os.system("pipenv run start")

    @sudo.command()
    async def load(self, ctx: Context, extension: str = None) -> None:
        """Load a cog."""
        if not extension:
            extension = self.bot.extension_list
        else:
            extension = f"bot.cogs.{extension}"

        for ext in extension:
            try:
                self.bot.load_extension(ext)
            except DiscordException:
                await ctx.send(f"```py\n{traceback.format_exc()}\n```")
            else:
                await ctx.send("\N{SQUARED OK}")

    @sudo.command()
    async def reload(self, ctx: Context, extension: str = None) -> None:
        if not extension:
            extension = self.bot.extension_list
        else:
            extension = f"bot.cogs.{extension}"

        for ext in extension:
            try:
                self.bot.unload_extension(ext)
                self.bot.load_extension(ext)
            except DiscordException:
                await ctx.send(f"```py\n{traceback.format_exc()}\n```")
            else:
                await ctx.send("\N{SQUARED OK}")

    @sudo.command()
    async def unload(self, ctx: Context, extension: str = None) -> None:
        if not extension:
            extension = self.bot.extension_list
        else:
            extension = f"bot.cogs.{extension}"

        for ext in extension:
            try:
                self.bot.unload_extension(ext)
            except DiscordException:
                await ctx.send(f"```py\n{traceback.format_exc()}\n```")
            else:
                await ctx.send("\N{SQUARED OK}")

    @sudo.command()
    async def stats(self, ctx: Context) -> None:
        """Show full bot stats."""
        implementation = platform.python_implementation()

        general = textwrap.dedent(
            f"""
            • Servers: **`{len(self.bot.guilds)}`**
            • Commands: **`{len(self.bot.commands)}`**
            • members: **`{len(set(self.bot.get_all_members()))}`**
            • Uptime: **{get_uptime(datetime.datetime.now() - self.start_time)}**
            """
        )
        system = textwrap.dedent(
            f"""
            • Python: **`{platform.python_version()} with {implementation}`**
            • discord.py: **`{discord_version}`**
            """
        )

        embed = Embed(title="BOT STATISTICS", color=Color.blue())
        embed.add_field(name="**❯❯ General**", value=general, inline=True)
        embed.add_field(name="**❯❯ System**", value=system, inline=True)
        embed.set_author(name=f"{self.bot.user.name}'s Stats", icon_url=self.bot.user.avatar_url)
        embed.set_footer(text=f"Made by {config.creator} Team.")

        await ctx.send(embed=embed)

    async def cog_check(self, ctx: Context) -> t.Union[bool, None]:
        """Only devs can use this."""
        if ctx.author.id in config.devs:
            return True

        embed = Embed(description="This is an owner-only command, you cannot invoke this.", color=Color.red())
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Owner(bot))

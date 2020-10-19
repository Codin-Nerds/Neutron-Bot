import os
import platform
import textwrap
import time
import traceback
import typing as t
from datetime import datetime

from discord import Color, DiscordException, Embed
from discord import __version__ as discord_version
from discord.ext.commands import Cog, Context, NotOwner, group

from bot import config
from bot.core.bot import Bot
from bot.utils import time as tm


class Sudo(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @group(hidden=True)
    async def sudo(self, ctx: Context) -> None:
        """Administrative information."""
        pass

    @sudo.command()
    async def shutdown(self, ctx: Context) -> None:
        """Turn the bot off."""
        await ctx.message.add_reaction("✅")
        await self.bot.close()

    @sudo.command()
    async def restart(self, ctx: Context) -> None:
        """Restart the bot."""
        await ctx.message.add_reaction("✅")
        await self.bot.close()

        time.sleep(1)
        os.system("pipenv run start")

    async def _manage_cog(self, ctx: Context, process: str, extension: t.Optional[str] = None) -> None:
        if not extension:
            extension = self.bot.extension_list
        else:
            extension = [f"bot.cogs.{extension}"]

        for ext in extension:
            try:
                if process == "load":
                    self.bot.load_extension(ext)
                elif process == "unload":
                    self.bot.unload_extension(ext)
                elif process == "reload":
                    self.bot.unload_extension(ext)
                    self.bot.load_extension(ext)
                else:
                    await ctx.send("Invalid process for extensions")
            except DiscordException:
                await ctx.send(f"```py\n{traceback.format_exc()}\n```")
            else:
                await ctx.send("\N{SQUARED OK}")

    @sudo.command()
    async def load(self, ctx: Context, extension: t.Optional[str]) -> None:
        await self._manage_cog(ctx, "load", extension)

    @sudo.command()
    async def unload(self, ctx: Context, extension: t.Optional[str]) -> None:
        await self._manage_cog(ctx, "unload", extension)

    @sudo.command()
    async def reload(self, ctx: Context, extension: t.Optional[str]) -> None:
        await self._manage_cog(ctx, "reload", extension)

    @sudo.command()
    async def stats(self, ctx: Context) -> None:
        """Show full bot stats."""
        general = textwrap.dedent(
            f"""
            • Servers: **`{len(self.bot.guilds)}`**
            • Commands: **`{len(self.bot.commands)}`**
            • Members: **`{len(set(self.bot.get_all_members()))}`**
            • Uptime: **{tm.stringify_reldelta(datetime.utcnow() - self.bot.start_time)}**
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
        embed.set_footer(text=f"Made by {config.creator} Team.")

        await ctx.send(embed=embed)

    async def cog_check(self, ctx: Context) -> t.Optional[bool]:
        """Only the bot owners can use this."""
        if ctx.author.id in config.devs:
            return True

        raise NotOwner


def setup(bot: Bot) -> None:
    bot.add_cog(Sudo(bot))

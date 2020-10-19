import textwrap

from discord import Color, Embed
from discord.ext.commands import Cog, Command, HelpCommand as OriginalHelpCommand

from bot.core.bot import Bot


class HelpCommand(OriginalHelpCommand):
    """The help command implementation."""

    def __init__(self):
        super().__init__(command_attrs={"help": "Shows help for given command / all commands"})

    async def fromat_command(self, command: Command) -> str:
        """Format a help message for given `command`."""
        parent = command.full_parent_name

        command_name = str(command) if not parent else f"{parent} {command.name}"
        command_syntax = f"{self.context.prefix}{command_name} {command.signature}"

        aliases = [f"`{alias}`" if not parent else f"`{parent} {alias}`" for alias in command.aliases]
        aliases = ", ".join(sorted(aliases))

        command_help = f"{command.help or 'No description provided.'}"

        message = textwrap.dedent(
            f"""
            Help syntax: `<Required arguments>`, `[Optional arguments]`

            **Syntax for {command_name}**:
            ```{command_syntax}```
            **Command description**
            *{command_help}*
            """
        )

        if aliases:
            message += f"\n\nAliases: {aliases}"
        if not await command.can_run(self.context):
            message += "**You don't have permission to use this command.**"

        return message

    async def send_command_help(self, command: Command) -> None:
        msg = await self.fromat_command(command)
        embed = Embed(
            title="Command Help",
            description=msg,
            color=Color.blue()
        )
        await self.context.send(embed=embed)
        # TODO: Schedule deletion


class Help(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = HelpCommand()

    def cog_unload(self) -> None:
        self.bot.help_command = self.old_help_command


def setup(bot: Bot) -> None:
    bot.add_cog(Help(bot))

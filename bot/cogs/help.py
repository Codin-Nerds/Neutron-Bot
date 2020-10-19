import textwrap
import typing as t

from discord import Color, Embed
from discord.ext.commands import Cog, Command, Group, HelpCommand as BaseHelpCommand
from discord.ext.commands.errors import CheckFailure
from discord.ext.menus import ListPageSource, Menu, MenuPages

from bot.core.bot import Bot


class HelpPages(ListPageSource):
    def __init__(self, embeds: t.List[Embed]):
        super().__init__(embeds, per_page=1)

    async def format_page(self, menu: Menu, embed: Embed) -> Embed:
        """Return the stored embed for current page."""
        return embed

    @classmethod
    def split_messages(
        cls,
        messages: t.List[str],
        initial_embed: t.Optional[Embed] = None,
        max_characters: int = 1024,
    ) -> "HelpPages":
        """
        Automatically split the given message into multiple embeds.

        Return an instance of this class with these embeds set as entries for the menu
        """
        split_messages = []
        index = 0
        for message in messages:
            try:
                stored_msg = split_messages[index]
            except IndexError:
                stored_msg = ""
                split_messages.append(stored_msg)

            if len(stored_msg + message) > max_characters:
                index += 1

            try:
                split_messages[index] += message
            except IndexError:
                split_messages.append(message)

        embeds = []
        if initial_embed:
            embeds.append(initial_embed)

        for page, message in enumerate(split_messages):
            embeds.append(
                Embed(
                    title=f"Page listing: {page + 1}",
                    description=message,
                    color=Color.blue()
                )
            )

        return cls(embeds)


class HelpCommand(BaseHelpCommand):
    """The help command implementation."""

    def __init__(self):
        super().__init__(command_attrs={"help": "Shows help for given command / all commands"})

    async def _describe_command(self, command: Command) -> t.Tuple[str, str, str, str]:
        if not await command.can_run(self.context):
            raise CheckFailure("You don't have permission to view help for this command.")

        parent = command.full_parent_name

        command_name = str(command) if not parent else f"{parent} {command.name}"
        command_syntax = f"{self.context.prefix}{command_name} {command.signature}"
        command_help = f"{command.help or 'No description provided.'}"

        aliases = [f"`{alias}`" if not parent else f"`{parent} {alias}`" for alias in command.aliases]
        aliases = ", ".join(sorted(aliases))

        return command_name, command_syntax, command_help, aliases

    async def _fromat_command(self, command: Command) -> Embed:
        """Format a help embed message for given `command`."""

        command_name, command_syntax, command_help, aliases = await self._describe_command(command)

        embed = Embed(
            title="Command Help",
            description="Help syntax: `<Required arguments>`, `[Optional arguments]`",
            color=Color.blue()
        )
        embed.add_field(
            name=f"Syntax for {command_name}",
            value=f"```{command_syntax}```",
            inline=False
        )
        embed.add_field(
            name="Command description",
            value=f"*{command_help}*",
            inline=False
        )
        if aliases:
            embed.add_field(name="Aliases", value=aliases, inline=False)

        return embed

    async def _format_group(self, group: Group) -> t.Union[Embed, HelpPages]:
        """Format a help embed message for giver `group`."""
        subcommands = group.commands

        # If a group doesn't have any subcommands, treat it as a group
        if len(subcommands) == 0:
            await self.send_command_help(group)

        subcommands = await self.filter_commands(subcommands, sort=True)

        embed = await self._fromat_command(group)

        messages = []
        for subcommand in subcommands:
            _, command_syntax, command_help, _ = await self._describe_command(subcommand)
            messages.append(textwrap.dedent(
                f"""
                `{command_syntax}`
                *{command_help}*
                """
            ))

        message = "".join(messages)

        # In case the message is too long (discord embed field limit is 1024)
        # Split it into multiple embeds and return `HelpPages` menus object
        if len(message) > 1024:
            return HelpPages.split_messages(messages)

        embed.add_field(
            name="Subcommands:",
            value=message,
            inline=False
        )

        return embed

    async def _format_cog(self, cog: t.Optional[Cog], commands: t.Optional[t.List[Command]] = None) -> Embed:
        """
        Format a help embed message for the given `cog`.

        If `commands` are provided, they'll be used without any additional filtering,
        otherwise commands will be detected from `cog` and filtered.

        In case `cog` is None, a help embed will be made for `commands` as unclassified commands.
        """
        if cog:
            cog_description = cog.description if cog.description else "No description provided"
        else:
            cog_description = ""

        embed = Embed(
            title=f"Help for {cog.qualified_name if cog else 'unclassified commands'}",
            description=textwrap.dedent(
                f"""
                Help syntax: `<Required arguments>`, `[Optional arguments]`

                {cog_description}

                """
            ),
            color=Color.blue()
        )

        if commands is None:
            commands = await self.filter_commands(cog.get_commands())

        for command in commands:
            parent = command.full_parent_name

            command_name = str(command) if not parent else f"{parent} {command.name}"
            command_syntax = f"{self.context.prefix}{command_name} {command.signature}"
            command_help = f"{command.help or 'No description provided.'}"

            embed.add_field(
                name=f"**`{command_syntax}`**",
                value=command_help,
                inline=False,
            )

        return embed

    async def send_bot_help(self, mapping: t.Dict[t.Optional[Cog], t.List[Command]]) -> None:
        """Send general bot help."""
        sorted_cogs = sorted(
            mapping,
            key=lambda cog: cog.qualified_name if cog else "ZZ"
        )
        cog_embeds = []
        for cog in sorted_cogs:
            commands = await self.filter_commands(mapping[cog])
            if commands:
                cog_embeds.append(await self._format_cog(cog, commands))

        pages = MenuPages(
            source=HelpPages(cog_embeds),
            clear_reactions_after=True
        )
        await pages.start(self.context)

    async def send_cog_help(self, cog: Cog) -> None:
        """Send help for specific cog."""
        embed = await self._format_cog(cog)
        await self.context.send(embed=embed)

    async def send_group_help(self, group: Group) -> None:
        """Send help for specific group."""
        formatted_help = await self._format_group(group)

        if isinstance(formatted_help, HelpPages):
            pages = MenuPages(
                source=formatted_help,
                clear_reactions_after=True
            )
            await pages.start(self.context)
        else:
            await self.context.send(embed=formatted_help)

    async def send_command_help(self, command: Command) -> None:
        """Send help for specific command."""
        embed = await self._fromat_command(command)
        await self.context.send(embed=embed)


class Help(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = HelpCommand()

    def cog_unload(self) -> None:
        self.bot.help_command = self.old_help_command


def setup(bot: Bot) -> None:
    bot.add_cog(Help(bot))

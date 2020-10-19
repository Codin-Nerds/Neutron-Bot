import textwrap
import typing as t
from collections import namedtuple

from discord import Color, Embed
from discord.ext.commands import Cog, Command, Group, HelpCommand as BaseHelpCommand
from discord.ext.commands.errors import CheckFailure

from bot.core.bot import Bot
from bot.utils.pages import EmbedPages

MAX_CHARACTERS = 400
field = namedtuple("field", ("name", "value"))


class HelpPages(EmbedPages):
    @staticmethod
    def _split_messages(messages: t.List[str], initial_length: int = 0) -> t.List[str]:
        split_messages = []
        index = 0
        for message in messages:
            try:
                stored_msg = split_messages[index]
            except IndexError:
                stored_msg = ""
                split_messages.append(stored_msg)

            length = len(stored_msg + message)

            if index == 0:
                length -= initial_length

            if length > MAX_CHARACTERS:
                index += 1

            try:
                split_messages[index] += message
            except IndexError:
                split_messages.append(message)

        return split_messages

    @staticmethod
    def _split_fields(fields: t.List[field], initial_length: int = 0) -> t.List[t.List[field]]:
        split_fields = []
        index = 0
        for fld in fields:
            try:
                stored_fields = split_fields[index]
            except IndexError:
                stored_fields = []
                split_fields.append(stored_fields)

            length = 0
            for stored_fld in stored_fields:
                length += len(stored_fld.name) + len(stored_fld.value)
            length += len(fld.name) + len(fld.value)

            if index == 0:
                length -= initial_length

            if length > MAX_CHARACTERS:
                index += 1

            try:
                split_fields[index].append(fld)
            except IndexError:
                split_fields.append([fld])

        return split_fields

    @staticmethod
    def _make_group_embeds(split_messages: t.List[str], initial_embed: Embed) -> t.List[Embed]:
        embeds = []
        initial_embed.add_field(
            name="Subcommands:",
            value=split_messages[0]
        )
        embeds.append(initial_embed)

        for page, message in enumerate(split_messages[1:]):
            embeds.append(
                Embed(
                    title=f"{initial_embed.title} {page + 2}",
                    description=message,
                    color=Color.blue()
                )
            )

        initial_embed.title = f"{initial_embed.title} 1"

        return embeds

    @staticmethod
    def _make_cog_embeds(fields: t.List[t.List[field]], initial_embed: Embed) -> t.List[Embed]:
        embeds = []
        for fld in fields[0]:
            initial_embed.add_field(
                name=fld.name,
                value=fld.value,
                inline=False
            )
        embeds.append(initial_embed)

        for page, page_fields in enumerate(fields[1:]):
            embed = Embed(
                title=f"{initial_embed.title} {page + 2}",
                color=Color.blue()
            )
            for fld in page_fields:
                embed.add_field(
                    name=fld.name,
                    value=fld.value,
                    inline=False
                )
            embeds.append(embed)

        initial_embed.title = f"{initial_embed.title} 1"

        return embeds

    @classmethod
    def split_group_commands(cls, cmd_messages: t.List[str], initial_embed: Embed) -> "HelpPages":
        """
        Automatically split the given group command messages into multiple embeds.

        Return an instance of this class with these embeds set as entries for the menu
        """
        split_messages = cls._split_messages(cmd_messages, len(initial_embed.description))
        embeds = cls._make_group_embeds(split_messages, initial_embed)
        return cls(embeds)

    @classmethod
    def split_cog_commands(cls, fields: t.List[field], initial_embed: Embed) -> "HelpPages":
        split_fields = cls._split_fields(fields, len(initial_embed.description))
        embeds = cls._make_cog_embeds(split_fields, initial_embed)
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

        # In case the message is too long
        # Split it into multiple embeds and return `HelpPages` menus object
        if len(message) > MAX_CHARACTERS:
            return HelpPages.split_group_commands(messages, initial_embed=embed)

        embed.add_field(
            name="Subcommands:",
            value=message,
            inline=False
        )

        return embed

    async def _format_cog(self, cog: t.Optional[Cog], commands: t.Optional[t.List[Command]] = None) -> t.Union[Embed, HelpPages]:
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

        fields = []
        for command in commands:
            _, command_syntax, command_help, _ = await self._describe_command(command)

            fields.append(
                field(
                    name=f"**`{command_syntax}`**",
                    value=command_help,
                )
            )

        length = 0
        for fld in fields:
            length += len(fld.name) + len(fld.value)

        if length > MAX_CHARACTERS:
            return HelpPages.split_cog_commands(fields, initial_embed=embed)

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
                formatted_help = await self._format_cog(cog, commands)
                if isinstance(formatted_help, HelpPages):
                    cog_embeds += formatted_help.embeds
                else:
                    cog_embeds.append(formatted_help)

        pages = EmbedPages(cog_embeds)
        await pages.start(
            self.context,
            clear_reactions_after=True
        )

    async def send_cog_help(self, cog: Cog) -> None:
        """Send help for specific cog."""
        formatted_help = await self._format_cog(cog)

        if isinstance(formatted_help, EmbedPages):
            await formatted_help.start(
                self.context,
                clear_reactions_after=True
            )
        else:
            await self.context.send(embed=formatted_help)

    async def send_group_help(self, group: Group) -> None:
        """Send help for specific group."""
        formatted_help = await self._format_group(group)

        if isinstance(formatted_help, EmbedPages):
            await formatted_help.start(
                self.context,
                clear_reactions_after=True
            )
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

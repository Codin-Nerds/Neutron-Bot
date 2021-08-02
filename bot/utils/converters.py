import re
import typing as t
from ast import literal_eval
from contextlib import suppress
from datetime import datetime

from dateutil.relativedelta import relativedelta
from discord import Member, User
from discord.errors import NotFound
from discord.ext.commands import Context
from discord.ext.commands.converter import Converter, MemberConverter, UserConverter
from discord.ext.commands.errors import BadArgument, ConversionError, MemberNotFound, UserNotFound
from loguru import logger

from bot.core.autoload import EXTENSIONS


def _obtain_user_id(argument: str) -> t.Optional[int]:
    """Get user ID from mention or directly from string."""
    mention_match = re.match(r'<@!?([0-9]+)>$', argument)
    id_match = re.match(r'([0-9]{15,21})$', argument)

    if mention_match is None and id_match is None:
        return None
    elif mention_match is not None:
        return int(mention_match.group(1))
    elif id_match is not None:
        return int(id_match.group(1))


class ActionReason(Converter):
    """Make sure reason length is within 512 characters."""

    async def convert(self, ctx: Context, argument: str) -> str:
        """Add ID to the reason and make sure it's withing length."""
        if argument != "":
            reason = f"[ID: {ctx.author.id}]: {argument}"
            if len(reason) > 512:
                reason_max = 512 - len(reason) + len(argument)
                raise BadArgument(f"Reason is too long ({len(argument)}/{reason_max})")
        else:
            reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"
        return reason


class Unicode(Converter):
    """Convert raw input into unicode formatted string."""

    @staticmethod
    def process_unicode(message: str) -> str:
        """
        Accept any string with raw unicode and convert it into proper unicode.
        It uses literal eval to process the string safely and turn it into proper unicode.
        """
        # Only process individual lines to avoid EOL in expression
        lines = message.split("\n")
        for index, line in enumerate(lines):
            try:
                # Replace ''' which would exit the string
                # even though it won't be allowed by literal_eval, it is still better
                # to replace it as it will properly evaluate even strings with that.
                line = line.replace("'''", "`<ESCAPE STRING>`")
                line = literal_eval(f"'''{line}'''")
                line = line.replace("`<ESCAPE STRING>`", "'''")
                lines[index] = line
            except SyntaxError as error:
                logger.info(f"Unicode message conversion failed on line: {line}, string considered unsafe ({error})")

        return "\n".join(lines)

    @staticmethod
    def outside_delimeter(string: str, delimeter: str, operation: t.Callable) -> str:
        """Apply given operation to text outside of delimeted section."""
        splitted = string.split(delimeter)
        for index, string_part in enumerate(splitted):
            # Not inside of a delimeted section
            if index % 2 == 0:
                splitted[index] = operation(string_part)

        return delimeter.join(splitted)

    async def convert(self, ctx: Context, argument: str) -> str:
        """Do the conversion."""
        # don't replace unicode characters within code blocks
        return self.outside_delimeter(
            argument,
            "```",
            lambda x: self.outside_delimeter(x, "`", self.process_unicode),
        )


class TimeDelta(Converter):
    """Convert given duration string into relativedelta."""

    time_getter = re.compile(
        r"((?P<years>\d+?) ?(y|yr|yrs|years|year) ?)?"
        r"((?P<months>\d+?) ?(mo|mon|months|month) ?)?"
        r"((?P<weeks>\d+?) ?(w|wk|weeks|week) ?)?"
        r"((?P<days>\d+?) ?(d|days|day) ?)?"
        r"((?P<hours>\d+?) ?(h|hr|hrs|hours|hour) ?)?"
        r"((?P<minutes>\d+?) ?(m|min|mins|minutes|minute) ?)?"
        r"((?P<seconds>\d+?) ?(s|sec|secs|seconds|second))?",
        re.IGNORECASE
    )

    async def convert(self, ctx: Context, duration: str) -> relativedelta:
        """
        Convert a string `duration` to relativedelta.
        Accepted inputs for `duration` (in order):
        * years: `y`, `yr`, `yrs`, `years`, `year`
        * months: `mo`, `mon`, `months`, `month`
        * weeks: `w`, `wk`, `weeks`, `week`
        * days: `d`, `days`, `day`
        * hours: `h`, `hr`, `hrs`, `hours`, `hour`
        * minutes: `m`, `min`, `mins`, `minutes`, `minute`
        * seconds: `s`, `sec`, `secs`, `seconds` `second`
        These inputs are case insensitive.
        """
        time_delta = self.time_getter.fullmatch(duration)
        if not time_delta:
            raise BadArgument("Invalid duration.")

        duration_dict = {unit: int(amount) for unit, amount in time_delta.groupdict(default=0).items()}
        return relativedelta(**duration_dict)


class Duration(TimeDelta):
    """Convert duration strings into amount of seconds"""

    async def convert(self, ctx: Context, duration: str) -> t.Union[int, float]:
        """
        Convert a `duration` string into a relativedelta using
        super `TimeDelta` converter. After that, simply change
        the relative delta into the amount of seconds it represents.

        Accepted inputs (in order):
        * infinity inputs: `-1`, `inf`, `infinity`, `infinite`
        * zero inputs: `0`, `none`, `null`
        * `TimeDelta` converter inputs
        """
        duration = duration.lower()

        if duration in ["-1", "inf", "infinite", "infinity"]:
            return float("inf")
        if duration in ["0", "none", "null"]:
            return 0

        delta = await super().convert(ctx, duration)

        now = datetime.utcnow()
        try:
            diff = (now + delta) - now
        except ValueError:
            raise BadArgument("Specified duration is outside maximum range.")

        return diff.total_seconds()


class Ordinal(Converter):
    """Convert integers to ordinal string representation"""
    @staticmethod
    def make_ordinal(n: int) -> str:
        """
        Convert an integer into its ordinal representation:
        * make_ordinal(0)   => "0th"
        * make_ordinal(3)   => "3rd"
        * make_ordinal(122) => "122nd"
        * make_ordinal(213) => "213th"
        """
        suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = "th"
        return str(n) + suffix

    async def convert(self, ctx: Context, number: str) -> str:
        if number.isdecimal():
            return self.make_ordinal(int(number))
        if number.endswith(("th", "st", "nd", "rd")):
            # Run conversion here, to prevent user inputted
            # invalid ordinals, i.e.: 3st
            if number[:-2].isdecimal():
                return self.make_ordinal(int(number[:-2]))
        raise ConversionError(f"{number} is not an ordinal number (`1st`, `2nd`, ...)")


class CodeBlock(Converter):
    """
    Convert given wrapped string in codeblock into a tuple of language and the wrapped string
    """

    codeblock_parser = re.compile(r"\`\`\`(.*\n)?((?:[^\`]*\n*)+)\`\`\`")
    inline_code_parser = re.compile(r"\`(.*\n*)\`")

    async def convert(self, ctx: Context, codeblock: str) -> t.Tuple[t.Optional[str], str]:
        """
        Convert a string `codeblock` into a tuple which consists of:
        * language (f.e.: `py` or `None` for no language)
        * wrapped_text (the text inside of the codeblock)
        The converter converts:
        * full codeblocks (```text```, ```py\ntext```, ```\ntext```)
        * inline codeblocks (`text`)
        In case no codeblock was found, original string is returned
        """
        codeblock_match = self.codeblock_parser.fullmatch(codeblock)
        if codeblock_match:
            lang = codeblock_match.group(1)
            code = codeblock_match.group(2)
            if not code:
                code = lang
                lang = None
            if code[-1] == "\n":
                code = code[:-1]
            return (lang, code)

        inline_match = self.inline_code_parser.fullmatch(codeblock)
        if inline_match:
            return (None, inline_match.group(1))

        return (None, codeblock)


class ValidExtension(Converter):
    """
    Convert given extension name to a full qualified path to extension.
    """
    @staticmethod
    def valid_extension_path(extension_name: str) -> str:
        """
        If given `extension_name` can be used to point to a single
        valid extension, return the full qualified path to it.

        `extension_name` can be a full qualified path ('bot.cogs.core.sudo'),
        or a unique suffix of a full qualified path (i.e. 'cogs.core.sudo',
        or 'core.sudo', or 'sudo'), as long as it only matches with single
        full qualified extension path, this path will be returned.

        If the extension_name can't uniquely point to a single full qualified
        path, raise ValueError
        """
        extension_name = extension_name.removeprefix("bot.cogs.")
        extension_name = extension_name.removeprefix("cogs.")
        if extension_name.startswith("bot."):
            raise ValueError("This path doesn't point to an extension.")

        # Check if full extension path matches
        if f"bot.cogs.{extension_name}" in EXTENSIONS:
            return f"bot.cogs.{extension_name}"

        # Check if extension_name is a child name, if it is and it's
        # unique to only one parent module, return that extension
        # (i.e. if extension_name='sudo', there's only 1 such child cog name
        # and that is within bot.cogs.core.sudo, so we can return it)
        possible_extensions = []
        for extension in EXTENSIONS:
            if extension.endswith(extension_name):
                possible_extensions.append(extension)

        if len(possible_extensions) == 1:
            return possible_extensions[0]

        raise ValueError(f"Extension {extension_name} wasn't found.")

    async def convert(self, ctx: Context, extension_name: str) -> str:
        """Try to match given `extension_name` to a valid extension within bot project."""
        try:
            return self.valid_extension_path(extension_name)
        except ValueError as exc:
            raise ConversionError(str(exc))


class ProcessedUser(UserConverter):
    """
    Try to convert any accepted string into `User`
    Lookup Strategy:
    [Default UserConverter strategy]
    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    [Added functionality]
    5. Lookup by API
    """

    async def convert(self, ctx: Context, argument: str) -> User:
        # Follow general MemberConverter lookup strategy
        with suppress(BadArgument):
            return await super().convert(ctx, argument)

        # Try to look user up using API
        ID = _obtain_user_id(argument)
        if ID is None:
            raise UserNotFound(f"No user found from `{argument}`")
        try:
            return await ctx.bot.fetch_user(ID)
        except NotFound:
            raise UserNotFound(f"No user with ID: {ID} found")


class ProcessedMember(MemberConverter):
    """
    Try to convert any accepted string into `Member`
    Lookup Strategy:
    [Default MemberConverter strategy]
    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    5. Lookup by nickname
    [Added functionality]
    6. Lookup by API
    """

    async def convert(self, ctx: Context, argument: str) -> Member:
        # Follow general MemberConverter lookup strategy
        with suppress(BadArgument):
            return await super().convert(ctx, argument)

        # Try to look user up using API
        ID = _obtain_user_id(argument)
        if ID is None:
            raise MemberNotFound(f"No member found on guild {ctx.guild.id} from `{argument}`")
        try:
            return await ctx.guild.fetch_member(ID)
        except NotFound:
            raise MemberNotFound(f"No member with ID: {ID} found on guild {ctx.guild.id}")

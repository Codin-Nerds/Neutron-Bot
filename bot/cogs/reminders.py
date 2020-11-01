from collections import defaultdict

from discord import Color, Embed, Member
from discord.ext.commands import Cog, Context, group
from discord.ext.commands.errors import BadArgument

from bot.core.bot import Bot
from bot.core.converters import Duration
from bot.core.timer import Timer
from bot.utils.time import stringify_duration


class Reminders(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.reminders = defaultdict(list)
        self.timer = Timer("reminder")

    async def _remind(self, author: Member, message: str) -> None:
        embed = Embed(
            title="Your reminder has arrived",
            description=message,
            color=Color.blue()
        )
        await author.send(embed=embed)

    @group(invoke_without_command=True, aliases=["reminders", "remind"])
    async def reminder(self, ctx: Context) -> None:
        """Commands for configuring the reminders."""
        await ctx.send_help(ctx.command)

    @reminder.command(alias=["create", "make", "remind"])
    async def add(self, ctx: Context, duration: Duration, *, message: str) -> None:
        """
        Send a reminder of given `message` after the specified `duration` expires.
        """
        if duration == float("inf"):
            raise BadArgument(":x: Duration can't be infinite")

        self.reminders[ctx.author].append(message)
        _task_name = f"{ctx.author.id}.{len(self.reminders[ctx.author])}"
        self.timer.delay(duration, _task_name, self._remind(ctx.author, message))

        await ctx.send(f"You'll be reminded in {stringify_duration(duration)}: {message}.")

    @reminder.command(aliases=["delete"])
    async def remove(self, ctx: Context, reminder_id: int) -> None:
        """
        Remove given reminder based on the `reminder_id`

        Reminder IDs are ordered numbers from 1, based on the order
        you created your reminders. For example reminder id 2 will be
        the second active reminder.
        """
        reminder_amount = len(self.reminders[ctx.author])
        if reminder_amount < reminder_id:
            if reminder_amount == 0:
                await ctx.send(":x: Sorry, you don't have any active reminders.")
            else:
                await ctx.send(f":x: Sorry, you don't have reminder with this ID. (Maximum ID: {reminder_amount})")
            return

        self.timer.abort(f"{ctx.author.id}.{reminder_id - 1}")
        del self.reminders[ctx.author][reminder_id - 1]

        await ctx.send(f"Reminder {reminder_id} has been cancelled.")


def setup(bot: Bot) -> None:
    bot.add_cog(Reminders(bot))

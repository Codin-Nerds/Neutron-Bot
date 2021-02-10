import textwrap

from discord import Color, Embed, Message
from discord.ext.commands import Cog
from loguru import logger

from bot.core.bot import Bot
from bot.core.converters import DiscordInvite


class InviteDetect(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """
        Check every message for valid discord invites as advertisement prevention.
        If an invite is found, and the user doesn't have manage messages rights in
        given channel, the message will be automatically removed.
        """
        valid_invite = DiscordInvite.extract_invite(message.content)
        if not valid_invite:
            return

        if message.author.permissions_in(message.channel).manage_messages:
            return

        logger.debug(f"User {message.author.id} has posted discord invite link: {valid_invite.string}")

        await message.delete()
        embed = Embed(
            title="Your message got zapped by our spam filter.",
            description=textwrap.dedent(
                """
                We don't allow posting discord invites, it is considered advertisement
                which we don't support, please avoid spamming them, or you will get muted.
                """
            ),
            color=Color.red()
        )
        await message.channel.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(InviteDetect(bot))

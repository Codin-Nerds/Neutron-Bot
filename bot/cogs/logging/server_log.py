import datetime
import typing as t

from discord import CategoryChannel, Color, Embed, TextChannel, VoiceChannel
from discord.abc import GuildChannel
from discord.ext.commands import Cog

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.utils.time import stringify_duration


class ServerLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @classmethod
    def make_channel_update_embed(cls, channel_before: GuildChannel, channel_after: GuildChannel) -> t.Optional[Embed]:
        embed = None

        if channel_before.overwrites != channel_after.overwrites:
            embed = cls._permissions_diff_embed(channel_before, channel_after)

        if isinstance(channel_before, TextChannel) and embed is None:
            slowmode_readable = lambda time: stringify_duration(time) if time != 0 else None
            embed = cls._specific_channel_update_embed(
                channel_before, channel_after,
                title="Text Channel updated",
                check_params={
                    "name": "Name",
                    "topic": "Topic",
                    "slowmode_delay": (slowmode_readable, "Slowmode delay"),
                    "category": "Category",
                }
            )
        if isinstance(channel_before, VoiceChannel) and embed is None:
            readable_bitrate = lambda bps: f"{round(bps/1000)}kbps"
            embed = cls._specific_channel_update_embed(
                channel_before, channel_after,
                title="Voice Channel updated",
                check_params={
                    "name": "Name",
                    "bitrate": (readable_bitrate, "Bitrate"),
                    "category": "Category",
                }
            )
        if isinstance(channel_before, CategoryChannel) and embed is None:
            embed = cls._specific_channel_update_embed(
                channel_before, channel_after,
                title="Category Channel updated",
                check_params={
                    "name": "Name",
                }
            )

        if embed is not None:
            embed.timestamp = datetime.datetime.now()

        return embed

    @staticmethod
    def _specific_channel_update_embed(
        channel_before: GuildChannel,
        channel_after: GuildChannel,
        title: str,
        check_params: dict
    ) -> t.Optional[Embed]:
        """
        Generate embed for difference between 2 passed channels.

        `check_params` is a dictionary which defines what variables should
        be compared.
        Keys should always be strings, referring to variable names.
        Values are either:
            * string: readable description of the update variable
            * tuple (callable, string): callable is ran which on obtained values for better readability
        """
        embed = Embed(
            title=title,
            description=f"**Channel:** {channel_after.mention}",
            color=Color.dark_blue()
        )

        field_before_text = []
        field_after_text = []

        for parameter_name, value in check_params.items():
            before_param = getattr(channel_before, parameter_name)
            after_param = getattr(channel_after, parameter_name)
            if before_param != after_param:
                if isinstance(value, tuple):
                    func = value[0]
                    before_param = func(before_param)
                    after_param = func(after_param)
                    # Continue with 2nd element (should be parameter name string)
                    value = value[1]
                if isinstance(value, str):
                    field_before_text.append(f"**{value}:** {before_param}")
                    field_after_text.append(f"**{value}:** {after_param}")

        if len(field_after_text) == 0:
            return

        embed.add_field(
            name="Before",
            value="\n".join(field_before_text),
            inline=True
        )
        embed.add_field(
            name="After",
            value="\n".join(field_after_text),
            inline=True
        )

        return embed

    @staticmethod
    def _permissions_diff_embed(channel_before: GuildChannel, channel_after: GuildChannel) -> t.Optional[Embed]:
        if isinstance(channel_before, TextChannel):
            channel_type = "Text channel"
        elif isinstance(channel_before, VoiceChannel):
            channel_type = "Voice channel"
        elif isinstance(channel_before, CategoryChannel):
            channel_type = "Category channel"

        embed_lines = []
        all_overwrites = set(channel_before.overwrites.keys()).union(set(channel_after.overwrites.keys()))

        for overwrite_for in all_overwrites:
            before_overwrites = channel_before.overwrites_for(overwrite_for)
            after_overwrites = channel_after.overwrites_for(overwrite_for)

            if before_overwrites == after_overwrites:
                continue

            embed_lines.append(f"**Overwrite changes for {overwrite_for.mention}:**")

            for before_perm, after_perm in zip(before_overwrites, after_overwrites):
                if before_perm[1] != after_perm[1]:
                    perm_name = before_perm[0].replace("_", " ").capitalize()

                    if before_perm[1] is True:
                        before_emoji = "✅"
                    elif before_perm[1] is False:
                        before_emoji = "❌"
                    else:
                        before_emoji = "⬜"

                    if after_perm[1] is True:
                        after_emoji = "✅"
                    elif after_perm[1] is False:
                        after_emoji = "❌"
                    else:
                        after_emoji = "⬜"

                    embed_lines.append(f"**`{perm_name}:`** {before_emoji} ➜ {after_emoji}")

        # Don't send an embed without permissions edited,
        # it only means that an override was added, but it's
        # staying with all permissions at `None`
        if len(embed_lines) == 0:
            return

        embed_text = f"{channel_after.mention} permissions have been updated.\n\n"
        embed_text += "\n".join(embed_lines)

        permissions_embed = Embed(
            title=f"{channel_type} permissions updated",
            description=embed_text,
            color=Color.dark_blue()
        )

        return permissions_embed

    @Cog.listener()
    async def on_guild_channel_update(self, channel_before: GuildChannel, channel_after: GuildChannel) -> None:
        embed = self.make_channel_update_embed(channel_before, channel_after)
        if embed is None:
            return

        server_log_id = await LogChannels.get_log_channel(self.bot.db_session, "server_log", channel_after.guild)
        server_log_channel = channel_after.guild.get_channel(server_log_id)
        if server_log_channel is None:
            return

        await server_log_channel.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(ServerLog(bot))

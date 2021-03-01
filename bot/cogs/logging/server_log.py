import datetime
import typing as t
from functools import partial

from discord import Color, Embed, Guild, Role
from discord.abc import GuildChannel
from discord.channel import CategoryChannel, TextChannel, VoiceChannel
from discord.enums import AuditLogAction
from discord.ext.commands import Cog

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.utils.audit_parse import last_audit_log_with_fail_embed
from bot.utils.time import stringify_duration


class ServerLog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_log(self, guild: Guild, *send_args, **send_kwargs) -> bool:
        """
        Try to send a log message to a server_log channel for given guild,
        args and kwargs to this function will be used in the actual `Channel.send` call.

        If the message was sent, return True, otherwise return False
        (might happen if server_log channel isn't defined in database).
        """
        server_log_id = await LogChannels.get_log_channel(self.bot.db_engine, "server_log", guild)
        server_log_channel = guild.get_channel(int(server_log_id))
        if server_log_channel is None:
            return False

        await server_log_channel.send(*send_args, **send_kwargs)
        return True

    # region: Channels

    @staticmethod
    def channel_path(channel: GuildChannel) -> str:
        """
        Format path to given channel without direct mentioning,
        if this channel will be removed afterwards, we can know which
        category it belonged to.
        """
        if channel.category:
            return f"{channel.category}/#{channel.name}"
        return f"#{channel.name}"

    def channel_type(self, channel: GuildChannel) -> str:
        """Classify given channel and return it's category name (str)."""
        if isinstance(channel, CategoryChannel):
            return "Category"
        elif isinstance(channel, VoiceChannel):
            return "Voice channel"
        return "Text channel"

    async def make_channel_update_embed(self, channel_before: GuildChannel, channel_after: GuildChannel) -> t.Optional[Embed]:
        embed = None

        if channel_before.overwrites != channel_after.overwrites:
            embed = await self._channel_permissions_diff_embed(channel_before, channel_after)
        elif isinstance(channel_before, TextChannel):
            slowmode_readable = lambda time: stringify_duration(time) if time != 0 else None
            embed = await self._specific_channel_update_embed(
                channel_before, channel_after,
                title="Text Channel updated",
                check_params={
                    "name": "Name",
                    "topic": "Topic",
                    "is_nsfw": (lambda is_nsfw_func: is_nsfw_func(), "NSFW"),
                    "slowmode_delay": (slowmode_readable, "Slowmode delay"),
                    "category": "Category",
                }
            )
        elif isinstance(channel_before, VoiceChannel):
            readable_bitrate = lambda bps: f"{round(bps/1000)}kbps"
            embed = await self._specific_channel_update_embed(
                channel_before, channel_after,
                title="Voice Channel updated",
                check_params={
                    "name": "Name",
                    "bitrate": (readable_bitrate, "Bitrate"),
                    "user_limit": "User limit",
                    "category": "Category",
                }
            )
        elif isinstance(channel_before, CategoryChannel):
            embed = await self._specific_channel_update_embed(
                channel_before, channel_after,
                title="Category Channel updated",
                check_params={
                    "name": "Name",
                    "is_nsfw": "NSFW",
                }
            )

        if embed is None:
            return

        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text=f"Channel ID: {channel_after.id}")

        return embed

    async def _specific_channel_update_embed(
        self,
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
        description = f"**Channel:** {channel_after.mention}"

        last_log = await last_audit_log_with_fail_embed(
            channel_after.guild,
            actions=[AuditLogAction.channel_update],
            send_callback=partial(self.send_log, channel_after.guild)
        )

        if last_log:
            description += f"\n**Updated by:** {last_log.user.mention}"

        embed = Embed(
            title=title,
            description=description,
            color=Color.dark_blue()
        )

        field_before_text = []
        field_after_text = []

        for parameter_name, value in check_params.items():
            before_param = getattr(channel_before, parameter_name)
            after_param = getattr(channel_after, parameter_name)
            if isinstance(value, tuple):
                func = value[0]
                before_param = func(before_param)
                after_param = func(after_param)
                # Continue with 2nd element (should be parameter name string)
                value = value[1]

            if before_param != after_param:
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

    async def _channel_permissions_diff_embed(self, channel_before: GuildChannel, channel_after: GuildChannel) -> t.Optional[Embed]:
        channel_type = self.channel_type(channel_after)

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

        description = f"**Channel:** {channel_after.mention}\n"

        last_log = await last_audit_log_with_fail_embed(
            channel_after.guild,
            actions=[AuditLogAction.overwrite_create, AuditLogAction.overwrite_delete, AuditLogAction.overwrite_update],
            send_callback=partial(self.send_log, channel_after.guild)
        )

        if last_log:
            description += f"**Updated by:** {last_log.user.mention}\n\n"

        description += "\n".join(embed_lines)

        permissions_embed = Embed(
            title=f"{channel_type} permissions updated",
            description=description,
            color=Color.dark_blue()
        )

        return permissions_embed

    @Cog.listener()
    async def on_guild_channel_update(self, channel_before: GuildChannel, channel_after: GuildChannel) -> None:
        embed = await self.make_channel_update_embed(channel_before, channel_after)
        if embed is None:
            return

        await self.send_log(channel_after.guild, embed=embed)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        last_log = await last_audit_log_with_fail_embed(
            channel.guild,
            actions=[AuditLogAction.channel_delete],
            send_callback=partial(self.send_log, channel.guild)
        )
        description = f"**Channel path:** {self.channel_path(channel)}"
        if last_log:
            description += f"\n**Removed by:** {last_log.user.mention}"

        embed = Embed(
            title=f"{self.channel_type(channel)} removed",
            description=description,
            color=Color.red()
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        embed.timestamp = datetime.datetime.utcnow()
        await self.send_log(channel.guild, embed=embed)

    @Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel) -> None:
        last_log = await last_audit_log_with_fail_embed(
            channel.guild,
            actions=[AuditLogAction.channel_create],
            send_callback=partial(self.send_log, channel.guild)
        )
        description = f"**Channel path:** {self.channel_path(channel)}"
        if last_log:
            description += f"\n**Created by:** {last_log.user.mention}"

        embed = Embed(
            title=f"{self.channel_type(channel)} created",
            description=description,
            color=Color.green()
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        embed.timestamp = datetime.datetime.utcnow()
        await self.send_log(channel.guild, embed=embed)

    # endregion
    # region: Roles

    @Cog.listener()
    async def on_guild_role_update(self, before: Role, after: Role) -> None:
        # TODO: Finish this
        pass

    @Cog.listener()
    async def on_guild_role_create(self, role: Role) -> None:
        last_log = await last_audit_log_with_fail_embed(
            role.guild,
            actions=[AuditLogAction.role_create],
            send_callback=partial(self.send_log, role.guild)
        )
        description = f"**Role:** {role.mention}"
        if last_log:
            description += f"\n**Created by:** {last_log.user.mention}"

        embed = Embed(
            title="Role created",
            description=description,
            color=Color.green()
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        embed.timestamp = datetime.datetime.utcnow()
        await self.send_log(role.guild, embed=embed)

    @Cog.listener()
    async def on_guild_role_delete(self, role: Role) -> None:
        last_log = await last_audit_log_with_fail_embed(
            role.guild,
            actions=[AuditLogAction.role_delete],
            send_callback=partial(self.send_log, role.guild)
        )

        description = f"**Role:** @{role.name}"

        if last_log:
            description += f"\n**Removed by:** {last_log.user.mention}"

        embed = Embed(
            title="Role deleted",
            description=description,
            color=Color.red()
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        embed.timestamp = datetime.datetime.utcnow()
        await self.send_log(role.guild, embed=embed)

    # endregion

    @Cog.listener()
    async def on_guild_update(self, before: Guild, after: Guild) -> None:
        # TODO: Finish this
        pass


def setup(bot: Bot) -> None:
    bot.add_cog(ServerLog(bot))

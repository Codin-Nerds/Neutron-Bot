import datetime
from functools import partial

from discord import Color, Embed, Guild, Role
from discord.abc import GuildChannel
from discord.channel import CategoryChannel, VoiceChannel
from discord.enums import AuditLogAction
from discord.ext.commands import Cog

from bot.core.bot import Bot
from bot.database.log_channels import LogChannels
from bot.utils.audit_parse import last_audit_log_with_fail_embed
from bot.utils.diff import add_change_field, add_channel_perms_field, add_permissions_field


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

    @Cog.listener()
    async def on_guild_channel_update(self, channel_before: GuildChannel, channel_after: GuildChannel) -> None:
        if channel_before.overwrites != channel_after.overwrites:
            description = f"**Channel:** {channel_after.mention}\n"

            last_log = await last_audit_log_with_fail_embed(
                channel_after.guild,
                actions=[AuditLogAction.overwrite_create, AuditLogAction.overwrite_delete, AuditLogAction.overwrite_update],
                send_callback=partial(self.send_log, channel_after.guild)
            )

            if last_log:
                description += f"**Updated by:** {last_log.user.mention}\n\n"

            embed = Embed(
                title=f"{self.channel_type(channel_after)} permissions updated",
                description=description,
                color=Color.dark_blue()
            )

            embed = add_channel_perms_field(embed, channel_before, channel_after)
        else:
            description = f"**Channel:** {channel_after.mention}"

            last_log = await last_audit_log_with_fail_embed(
                channel_after.guild,
                actions=[AuditLogAction.channel_update],
                send_callback=partial(self.send_log, channel_after.guild)
            )

            if last_log:
                description += f"\n**Updated by:** {last_log.user.mention}"

            embed = Embed(
                title=f"{self.channel_type(channel_after)} updated",
                description=description,
                color=Color.dark_blue()
            )
            embed = add_change_field(embed, channel_before, channel_after)

        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text=f"Channel ID: {channel_after.id}")

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
        description = f"**Role:** {after.mention}"

        last_log = await last_audit_log_with_fail_embed(
            after.guild,
            actions=[AuditLogAction.role_update],
            send_callback=partial(self.send_log, after.guild)
        )

        embed = Embed(
            title="Role updated",
            description=description,
            color=Color.dark_gold()
        )

        if last_log:
            description += f"\n**Updated by:** {last_log.user.mention}"

        if before.permissions != after.permissions:
            embed = add_permissions_field(embed, before.permissions, after.permissions)
        else:
            embed = add_change_field(embed, before, after)

        embed.timestamp = datetime.datetime.now()

        await self.send_log(after.guild, embed=embed)

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
        description = "Guild configuration has changed."

        last_log = await last_audit_log_with_fail_embed(
            after,
            actions=[AuditLogAction.guild_update],
            send_callback=partial(self.send_log, after)
        )

        if last_log:
            description += f"\n**Updated by:** {last_log.user.mention}"

        embed = Embed(
            title="Guild updated",
            description=description,
            color=Color.dark_gold()
        )
        embed = add_change_field(embed, before, after)

        embed.timestamp = datetime.datetime.now()

        await self.send_log(after, embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(ServerLog(bot))

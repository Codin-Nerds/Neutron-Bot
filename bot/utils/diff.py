import typing as t
from collections import namedtuple

from deepdiff import DeepDiff
from discord import Embed, Guild
from discord.abc import GuildChannel
from discord.channel import TextChannel, VoiceChannel

from bot.utils.time import stringify_duration


format_mapping = {
    TextChannel: {
        "slowmode_delay": lambda time: stringify_duration(time) if time != 0 else 'Off'
    },
    VoiceChannel: {
        "bitrate": lambda bps: f"{round(bps/1000)}kbps"
    },
    Guild: {
        "afk_timeout": lambda time: stringify_duration(time)
    }
}


ValueUpdate = namedtuple("ValueUpdate", ("attr_name", "old_value", "new_value"))


def compare_objects(obj_before: t.Any, obj_after: t.Any,) -> t.List[ValueUpdate]:
    """
    Compare passed objects `obj_before` and `obj_after`.
    Return list of (named)tuples describing each found value update:
    `(attribute name, old value, new value)`
    """
    diff = DeepDiff(obj_before, obj_after)
    diff_values = diff.get("values_changed", {})
    diff_values.update(diff.get("type_changes", {}))

    changes = []
    for attr_name, value in diff_values.items():
        attr_name = attr_name.replace("root.", "")

        new = value["new_value"]
        old = value["old_value"]

        changes.append(ValueUpdate(attr_name=attr_name, new_value=new, old_value=old))

    return changes


def add_change_field(
    embed: Embed,
    obj_before: t.Any,
    obj_after: t.Any,
    mapping_override: t.Optional[dict] = None
) -> Embed:
    """
    Compare passed objects `obj_before` and `obj_after`.
    Return the passed embed with 2 new fields, containing formatted differences between
    these 2 objects. Returned object is a new Embed, to avoid mutating original.
    """
    if mapping_override is None:
        mapping_override = {}

    # Preserve original objects and work on copies
    embed = embed.copy()
    mapping_override = mapping_override.copy()

    mapping_override.update(format_mapping)

    field_before_lines = []
    field_after_lines = []

    for attr_name, old, new in compare_objects(obj_before, obj_after):
        # Try to go through `format_mapping` dictionary and check if there is
        # so type, which matches our current objects, if there is, check it's
        # mapping and apply the format function from it to our obtained values.
        for obj_type in mapping_override:
            if isinstance(obj_after, obj_type):
                func = format_mapping[obj_type].get(attr_name, lambda x: x)
                new = func(new)
                old = func(old)
                break

        attr_name = attr_name.replace("_", " ").capitalize()

        field_before_lines.append(f"**{attr_name}:** {old}")
        field_after_lines.append(f"**{attr_name}:** {new}")

    embed.add_field(
        name="Before",
        value="\n".join(field_before_lines),
        inline=True
    )
    embed.add_field(
        name="After",
        value="\n".join(field_after_lines),
        inline=True
    )

    return embed


def add_channel_perms_field(
    embed: t.Optional[Embed],
    channel_before: GuildChannel,
    channel_after: GuildChannel,
) -> Embed:
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
                perm_name = before_perm[0].replace("_", " ").replace(".", " ").capitalize()

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

    embed = embed.copy()
    embed.add_field(
        name="Details",
        value="\n".join(embed_lines),
        inline=False
    )

    return embed

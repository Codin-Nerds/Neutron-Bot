import dataclasses
import typing as t
from collections import namedtuple

from deepdiff import DeepDiff
from discord import Embed, Guild
from discord.abc import GuildChannel
from discord.channel import TextChannel, VoiceChannel
from discord.permissions import Permissions

from bot.utils.time import stringify_duration


format_mapping = {
    TextChannel: {
        "slowmode_delay": lambda time: stringify_duration(time) if time != 0 else 'Off'
    },
    VoiceChannel: {
        "bitrate": lambda bps: f"{round(bps/1000)}kbps"
    },
    Guild: {
        "afk_timeout": lambda time: stringify_duration(time),
        "_large": None
    }
}


ValueUpdate = namedtuple("ValueUpdate", ("attr_name", "old_value", "new_value"))
PermissionFlags = dataclasses.make_dataclass(cls_name="PermissionsHolder", fields=Permissions.VALID_FLAGS)


def _get_format_mapping_for(obj: t.Any, mapping_override: t.Optional[dict] = None) -> t.Dict[str, t.Optional[t.Callable]]:
    """
    Perform a linear search on `format_mapping` to check, which type matches
    given `object`, we can't perform a normal dict key lookup, because this
    might be used with inheritance, which would result in mapping not being
    detected for given superclass, even though the parent class was listed.

    By default, this will only search for entries in `format_mapping`, but if
    `mapping_override` is set, we will extend the found rules with this override,
    making it possible to override default values in `format_mapping` and apply
    custom formatting rules on top of the default ones.
    Example of this override mapping:
    ```py
    mapping_override = {
        "overridden attribute": lambda x: f"{x} seconds",
        "not shown attribute": None
    }
    ```
    """
    found_format_rules = {}

    for formatting_for, format_rules in format_mapping.items():
        if isinstance(obj, formatting_for):
            found_format_rules.update(format_rules)
            break

    if mapping_override is not None:
        found_format_rules.update(mapping_override)

    return found_format_rules


def compare_objects(
    obj_before: t.Any,
    obj_after: t.Any,
    use_format_mapping: bool = True,
    mapping_override: t.Optional[dict] = None
) -> t.List[ValueUpdate]:
    """
    Compare passed objects `obj_before` and `obj_after`.
    Return list of (named)tuples describing each found value update:
    `(attribute name, old value, new value)`

    By default, `format_mapping` dict will be followed and the values
    will bre reformatted accordingly, if this isn't desired, you can
    set `use_format_mapping` to `False`. You can also set `mapping_override`
    which will act on top of `format_mapping`. This mapping looks like this:
    ```py
    mapping_override = {
        "overridden attribute": lambda x: f"{x} seconds",
        "not shown attribute": None
    }
    ```
    """
    diff = DeepDiff(obj_before, obj_after)
    diff_values = diff.get("values_changed", {})
    diff_values.update(diff.get("type_changes", {}))

    if use_format_mapping:
        format_rules = _get_format_mapping_for(obj_before, mapping_override)
    else:
        format_rules = {}

    changes = []
    for attr_name, value in diff_values.items():
        attr_name = attr_name.replace("root.", "")

        new = value["new_value"]
        old = value["old_value"]

        formatting = format_rules.get(attr_name, lambda x: x)
        # Setting formatting to `None` should skip the variable
        if formatting is None:
            continue

        new = formatting(new)
        old = formatting(new)

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

    `mapping_override` can be set, which provides an easy way of ignoring or editing the
    values comming from the diff. This mapping looks like this:
    {
        "overridden attribute": lambda x: f"{x} seconds",
        "not shown attribute": None
    }
    """
    if mapping_override is None:
        mapping_override = {}

    # Preserve original objects and work on copies
    embed = embed.copy()

    field_before_lines = []
    field_after_lines = []

    for attr_name, old, new in compare_objects(obj_before, obj_after, mapping_override):
        attr_name = attr_name.replace("_", " ").replace(".", " ").capitalize()
        new = str(new).replace("_", " ")
        old = str(old).replace("_", " ")

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
    """
    Compare overwrites fo passed channels `channel_before` and `channel_after`.
    Return the passed embed with a new field, containing formatted differences between
    channel permission overrides. Returned object is a new Embed, to avoid mutating original.
    """
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


def add_permissions_field(
    embed: t.Optional[Embed],
    permissions_before: Permissions,
    permissions_after: Permissions,
) -> Embed:
    """"
    Compare permissions fo passed channels `channel_before` and `channel_after`.
    Return the passed embed with a new field, containing formatted differences between
    permission flags. Returned object is a new Embed, to avoid mutating original.
    """
    before_flag_dict = {flag: getattr(permissions_before, flag, None) for flag in Permissions.VALID_FLAGS}
    after_flag_dict = {flag: getattr(permissions_after, flag, None) for flag in Permissions.VALID_FLAGS}

    before_flags = PermissionFlags(**before_flag_dict)
    after_flags = PermissionFlags(**after_flag_dict)

    return add_change_field(embed, before_flags, after_flags)

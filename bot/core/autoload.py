import importlib
import inspect
import pkgutil
import typing as t
from types import FunctionType, ModuleType

import bot.cogs
import bot.database


def bare_name(name: str) -> str:
    """Return a bare (unqualified) name given a qualified module/package `name`."""
    return name.rsplit(".", maxsplit=1)[-1]


def readable_name(name: str) -> str:
    """
    Return uncluttered name by removing first 2 directories
    (without `bot.X.`, which is in every extension/database anyway).
    """
    return name.split(".", maxsplit=2)[-1]


def walk_modules(package: ModuleType, check: t.Optional[FunctionType] = None) -> t.Iterator[str]:
    """Yield extension names from the bot.cogs subpackage."""

    def on_error(name: str) -> t.NoReturn:
        raise ImportError(name=name)  # pragma: no cover

    for module in pkgutil.walk_packages(package.__path__, f"{package.__name__}.", onerror=on_error):
        if bare_name(module.name).startswith("_"):
            # Ignore module/package names starting with an underscore.
            continue

        if check and not check(module):
            continue

        yield module.name


def extension_check(module: ModuleType) -> bool:
    if module.ispkg:
        imported = importlib.import_module(module.name)
        # If it lacks a setup function, it's not an extension.
        return inspect.isfunction(getattr(imported, "setup", None))
    return True


EXTENSIONS = frozenset(walk_modules(bot.cogs, extension_check))
DATABASES = frozenset(walk_modules(bot.database))

import typing as t

from discord import Embed
from discord.ext.commands import Context
from discord.ext.menus import ListPageSource, Menu, MenuPages


class EmbedPages(ListPageSource):
    def __init__(self, embeds: t.List[Embed], embeds_per_page: int = 1):
        self.embeds = embeds
        super().__init__(embeds, per_page=embeds_per_page)

    async def format_page(self, menu: Menu, embed: Embed) -> Embed:
        """Return the stored embed for current page."""
        return embed

    async def start(self, ctx: Context, **menupages_kwargs) -> None:
        pages = MenuPages(
            source=self,
            **menupages_kwargs
        )
        await pages.start(ctx)

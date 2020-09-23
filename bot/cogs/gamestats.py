from discord.ext.commands import Cog

from bot.core.bot import Bot


class GameStats(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        
@command()
async def minecraft(self, ctx: Context, username: str) -> None:
  async with self.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", headers={'Accept': 'application/json'}) as session:
    uuid = await session.json()
  await ctx.send(uuid["id"])        
        

def setup(bot: Bot) -> None:
    bot.add_cog(GameStats(bot))

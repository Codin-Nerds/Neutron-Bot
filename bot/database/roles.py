from bot.core.bot import Bot
from bot.database import DBTable, Database


class Roles(DBTable):
    populate_command = """
        CREATE TABLE IF NOT EXISTS roles (
            serverid NUMERIC(40) UNIQUE NOT NULL,
            judge_role NUMERIC(40) DEFAULT 0,
            participant_role NUMERIC(40) DEFAULT 0
        )
        """

    def __init__(self, bot: Bot, database: Database):
        super().__init__(database)
        self.bot = bot
        self.database = database


async def load(bot: Bot, database: Database) -> None:
    await database.load_table(Roles(bot, database))

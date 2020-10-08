# Contributing Guide

This project is fully open-sourced and will be automatically deployed whenever commits are pushed to `master` branch, so these are the guidelines to keep everything clean and in working order.

Note that contributions may be rejected on the basis of a contributor failing to follow these guidelines

## Rules

1. **No force-pushes** or modifying the Git history in any way.
2. If you have direct access to the repository **Create a branch for your changes** and create a pull request for that branch. If not, create a branch on a for of the repository and create a pull request from there.
   * It's common practice for repository to reject direct pushes to `master`, so make branching a habit!
   * If PRing from your own fork, **ensure that "Allow edits from maintainers" is checked**. This gives permission for maintainers to commit changes directly to your fork, speeding up the review process.
3. **Adhere to the prevailing code style** which we enforce using [`flake8`](https://flake8.pycqa.org/en/latest/index.html) and [`pre-commit`](https://pre-commit.com/).
   * Run `flake8` and `pre-commit` against your code before you push it.
   * [Git hooks](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) are a powerful git feature for executing custom scripts when certain important git actions occur. The pre-commit hook is the first hook executed during the commit process and can be used to check the code being commited & abort the commit if issues, such as linting failures are detected. While git hooks can seem daunting to configure, the `pre-commit` framework abstracts this process away from you and is provided as a dev dependency for this project. Run `pipenv run pre-commit` when setting up the project and you'll never have to worry about commiting your code that fails linting.
4. **Make great commits**. A well structured git log is key to a project's maintainability; it efficiently provides insight into when and why things were done for future maintainers of the project.
    * Commits should be as narrow in scope as possible. Commits that span hundreds of lines across multiple unrelated functions and/or files are very hard for maintainers to follow. After about a week they'll probably be hard for you to follow too.
    * Avoid making minor commits for fixing typos or linting errors. Since you've already set up a `pre-commit` hook to run the linting pipeline before a commit, you shouldn't be commiting linting issues anyway.
    * A more in-depth guide to writing great commit messages can be found in Chris Beam's [*How to Write a Git Commit Message*](https://chris.beams.io/posts/git-commit/)
5. **Avoid frequent pushes to the main repository**. This goes for PRs opened against your fork as well. Try to batch your commits until you've finished working for that session, or you've reached a point where collaborators need your commits to continue their own work. This also provides you the opportunity to ammend commits for minor changes rather than having to commit them on their own because you've already pushed.
    * This includes merging master into your branch. Try to leave merging from master for after your PR passes review: a maintainer will bring your PR up to date before merging. Exceptions to this include: resolving merge conflicts, needing something that was pushed to master for your branch, or something was pushed to master that could potentially affect the functionality of what you're doing
6. **Don't fight the framework**. Every framework has its laws, but the frameworks we've picked out have been carefully chosen for their particular merits. If you can avoid it, please resist reimplementing swathes or framework logic - the work has already been done for you!
7. If someone is working on an issue or pull request. **do not open your own pull request for the same task**. Instead, collaborate with the author(s) of the existing pull request. Duplicate PRs opened without communicating with the other author(s) and/or repository authors will be closed. Communication is key, and there's no point in two separate implementations of the same thing.
    * One option is to fork the other contributor's repository and submit your changes to their branch with your own pull request. We suggest following these guidelines when interacting with their repository as well.
    * The author(s) of inactive PRs and claimed issues will be pinged after a week of inactivity for an update. Continued inactivity may result in the issue being released back to the community and/or PR closure.
8. **Work as a team** and collaborate whenever possible. Keep things friendly and help each other out - these are shared projects and nobody likes to have their feet trodded on.
9. All static content, such as images or audio, **must be licensed for open public use**.
    * Static content must be hosted by a service designed to do so. Failing to do so is known as "leeching" and is frowned upon, as it generates extra bandwidth to the host without providing benefit. It would be best if appropriately licensed content is added to the repository itself.

Above all, the needs of our community should come before the wants of an individual. Work together, build solutions to problems and try to do so in a way that people can learn from easily. Abuse of our trust may result in the loss of your Contributor role.

## Type Hinting

[PEP 484](https://www.python.org/dev/peps/pep-0484/) formally specifies type hints for Python functions, added to the Python Standard Library in version 3.5. Type hints are recognized by most modern code editing tools and provide useful insight into both the input and output types of a function, preventing the user from having to go through the codebase to determine these types.

For example:

```py
import typing as t


def foo(input_1: int, input_2: t.Dict[str, str]) -> bool:
    ...
```

Tell us that `foo` accepts an `int` and a `dict` with `str` keys and values, and returns a `bool`.

All functions declarations should be type hinted in code contributed to this repository

## Docstring Formatting Directive

Many documentation packages provide support for automatic documentation generation from the codebase's docstrings. These tools utilize special formatting directives to enable richer formatting in the generated documentation.

For example:

```py
import typing as t


def foo(bar: int, baz: t.Optional[t.Dict[str, str]] = None) -> bool:
    """
    Does some things with some stuff.

    :param bar: Some input
    :param baz: Optional, some dictionary with string keys and values

    :return: Some boolean
    """
    ...
```

Since we don't utilize automatic documentation generation, use of this syntax should not be used in the code contributed here. Should the purpose and type of the input variables not be easily discernable from the variable name and type annotation a prose explanation can be used. Explicit references to variables, function, classes, etc. should be wrapped with backticks (`` ` ``)

For example, the above docstring would become:

```py
import typing as t


def foo(bar: int, baz: t.Optional[t.Dict[str, str]] = None) -> bool:
    """
    Does some things with some stuff.

    This function takes an index, `bar` and checks for its presence in the database `baz`, passed as a dictionary. Returns `False` if `baz` is not passed.
    """
    ...
```

To provide further instruction on our docstring formatting syntax, here are the formatting options

```py
from discord.ext.commands import Context, command

@command()
def foo(ctx: Context, value: str) -> None:
  """Short description of a command."""

@command()
def bar(ctx: Context, value: str) -> None:
  """
  Longer single-line description of a command.
  """

@command()
def foobar(ctx: Context, value: str) -> None:
  """
  Title for a longer description (might also be a short explanation).

  Detailed multiline description.
  This may include the full explanation of how this command works.

  We can also have multiple sections like this.
  Or when necessary a list of accepted parameters and their explanation.

  Parameters:
  * value: str
      This is the `value` of this command.
      It is only a placeholder for this very explanation.
  """
```

Note that we end each sentence in docstrings with `.` to keep everything consistent

## Database table management

We use a custom way to define our database tables, this was implemented in [PR #11](https://github.com/Codin-Nerds/Neutron-Bot/pull/11) and updated in [PR #14](https://github.com/Codin-Nerds/Neutron-Bot/pull/14)
You can check those pull requests as they explains in detail what was added and how to use it.

### Making a new table

Every database table needs to have a it's own file. This file should be named by the table name (although this isn't mandatory).
This file needs to be stored under the `bot/database` directory and it should look like this:

```py
import asyncpg

from bot.core.bot import Bot
from bot.database import DBTable, Database


class Roles(DBTable):
    columns = {
        "serverid": "NUMERIC(40) UNIQUE NOT NULL",
        "_default": "NUMERIC(40) DEFAULT 0",
        "muted": "NUMERIC(40) DEFAULT 0",
        "staff": "NUMERIC(40) DEFAULT 0",
    }

    def __init__(self, bot: Bot, database: Database):
        super().__init__(database, "roles")
        self.bot = bot
        self.database = database

    async def set_staff_role(self, server_id: int, role_id: int) -> None:
        await self.db_upsert(
            columns=["serverid", "staff_role"],
            values=[server_id, role_id],
            conflict_columns=["serverid"]
        )

    async def get_staff_role(self, server_id: int) -> asyncpg.Record:
        return await self.db_get(
            columns="staff_role",
            specification="serverid=$1",
            sql_args=[guild.id]
        )


async def load(bot: Bot, database: Database) -> None:
    await database.add_table(Roles(bot, database))
```

You can see the use of a `load` function on the bottom of the file, similarly to what discord.py uses for cogs.

You can also notice the absence of `SQL` code in the `set_staff_role` and `get_staff_role`, this is because of the custom built functions to make the process of managing the database table easier and it's also considered more readable.

There are a total of 3 functions like this which provide the SQL abstraction layer: `DBTable.db_upsert`, `DBTable.db_get`, and `DBTable.db_set`. In case you'd need something more specific you will have to fall back to the SQL query, you can execute this query using `DBTable.db_execute(sql, [arg1, arg2])` or if you want to obtain data from the database, you can use the `DBTable.db_fetchone(sql, [arg1, arg2])` or `DBTable.db_fetch(sql, [arg1, arg2])`.

The `columns` class attribute on the top holds the column table structure which will be used for initial creation the table. The populate command will be executed automatically when the table loads and it will use the given sql arguments defined in the values of this dictionary.

After you've created your table file, you'll need to reference it in the `db_tables` list defined in [`bot/__main__.py`](https://github.com/Codin-Nerds/Neutron-Bot/blob/master/bot/__main__.py).

The table will be loaded with the bots initiation automatically.

### Using caching

The database system also introduces a built-in way to easily use caching for your database. This means you can use synchronous functions to read your database from cache rather than making asynchronous calls to the database itself and reading it from there. Not only does that means you don't have to use async functions, it also makes accessing the database data faster.

Even through it's advantages, there are cases where caching isn't wanted in order to prevent using up too much memory. If this is your case, you don't have to do absolutely anything, just make the database as described in the section above, but if you do want caching, just read along.

In order to use caching, all you need to do is specify the `caching` class parameter, similarly to the `columns` parameter, except this one is optional. By including it the lower-level methods will automatically populate a `self.cache` dictionary for you based on your caching structure in this dictionary. This class variable looks like this:

```py
class FooTable(DBTable):
    caching = {
        "key": (int, "serverid"),

        "_default": int,
        "muted": (int, 0),
        "staff": None
    }
   ...
```

The `"key"` is used to hold the column which will be used as a unique identifier, under which the other column values will be stored, you can think of it as the primary key for caching. This is the key you'll use to access the cache itself (`self.cache[some_serverid]`).

The rest of the values follow simple syntax guidelines: the key represents the name of that column, and the value can be one of the 3 examples shown above:

1. **`int`**: This value definition only provides the datatype which this column should be using. This is the type that will be used to convert the `asyncpg.Record`. in this case, the following would be stored to cache `int(specific_record)`
2. **`(int, 0)`**: This acts similarly to the above except it also provides a default value of `0`.
3. **`None`**: This syntax will assume the same as the one with the pure data type, but the data type will be set to `t.Any` rather than something specific. If this type is used, you'll be storing the `asyncpg.Record` instances rather than any specified data type.

In order to get the values from your cache you can use 2 new getter/setter methods: `DBTable.cache_get(key, column)` and `DBTable.cache_update(key, column, value)`. Usage of these methods can be seen in a full table example here:

```py
class FooTable(DBTable):
    columns = {
        "serverid": "NUMERIC(40) UNIQUE NOT NULL",
        "_default": "NUMERIC(40) DEFAULT 0",
        "muted": "NUMERIC(40) DEFAULT 0",
        "staff": "NUMERIC(40) DEFAULT 0",
    }
    caching = {
        "key": (int, "serverid"),

        "_default": (int, 0),
        "muted": (int, 0),
        "staff": (int, 0)
    }

    def __init__(self, bot: Bot, database: Database):
        super().__init__(database, "roles")
        self.bot = bot
        self.database = database

    async def _set_role(self, role_name: str, guild_id: int, role_id: int) -> None:
        """Set a `role_name` column to store `role_id` for the specific `guild_id`."""
        await self.db_upsert(
            columns=["serverid", role_name],
            values=[guild_id, role_id],
            conflict_columns=["serverid"]
        )
        self.cache_update(guild.id, role_name, role.id)  # Cache setter function

    def _get_role(self, role_name: str, guild_id: int) -> int:
        """Get a `role_name` column for specific `guild_id` from cache."""
        return self.cache_get(guild_id, role_name)  # Cache getter function
```

### Referencing the database inside of your cogs

After that you've set up your database table classes with your custom functions, you're ready to use them inside of a cog, doing that is pretty simple:

```py
from discord.ext.commands import Cog

from bot.core.bot import Bot
from bot.database.roles import Roles, Context, command

class Foo(Cog):
    def __init__(self, bot: bot):
        self.bot = bot
        self.roles_db: Roles = Roles.reference()

    async def set_staff(self, ctx: Context, staff_role_id: int) -> None:
        await self.roles_db.set_staff_role(ctx.guild.id, staff_role_id)
```

Notice that the type of `self.roles_db` is hard defined. This is because the return type `Roles.reference()` is only set to an instance of `DBTable` not the specific table. That means that if you didn't hard define the type hint for it, your code editor won't be able to provide meaningful suggestions from that database table class.

## Work in Progress (WIP) PRs

Github provides a PR feature that allows PR author to mark it as WIP. This provides both a visual and functional indicator that the contents of the PR are in a draft state and not yet ready for formal review.

This feature should be utilized in place of the traditional method of prepending \[WIP\] to the PR title.

Methods of marking PR as a draft:

1. When creating it

   ![image](https://user-images.githubusercontent.com/20902250/94499351-bc736e80-01fc-11eb-8e99-a7863dd1428a.png)
2. After it was crated

   ![image](https://user-images.githubusercontent.com/20902250/94499276-8930df80-01fc-11eb-9292-7f0c6101b995.png)

As stated earlier **ensure that "Allow edits from maintainers" is checked** This gives permission for maintainers to commit changes directly to your fork, speeding up the review process.

## Changes to this Arrangement

All projects evolve over time, and this contribution guide is no different. This document is open to pull requests or changes by contributors. If you believe you have something valuable to add or change, please don't hesitate to do so in a PR.

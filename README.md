# Neutron Bot

[![mit](https://img.shields.io/badge/Licensed%20under-GPL-red.svg?style=flat-square)](./LICENSE)
![Python package](https://github.com/Codin-Nerds/Neutron-Bot/workflows/Python%20package/badge.svg)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python%203.8-ffe900.svg?longCache=true&style=flat-square&colorB=00a1ff&logo=python&logoColor=88889e)](https://www.python.org/)
[![Discord](https://img.shields.io/static/v1?label=The%20Codin'%20Nerds&logo=discord&message=%3E500%20members&color=%237289DA&logoColor=white)](https://discord.gg/Dhz9pM7)

## About the bot

Neutron is still in the early development stage so there aren't many features available yet but we're aiming to change that soon.

## Installation

If you want to run this bot on your own, you can simply follow this guide:

### Creating the bot on Discord

1. Create bot on Discord's [bot portal](https://discord.com/developers/applications/)
2. Make a **New Application**
3. Go to **Bot** settings and click on **Add Bot**
4. Make sure to give the bot indents it needs, this bot requires **server member intent**
5. Give **Administrator** permission to bot
6. You will find your bot **TOKEN** there, it is important that you save it
7. Go to **OAuth2** and click bot, than add **Administrator** permissions
8. You can follow the link that will appear to add the bot to your discord server

### Docker

You can run your application contained within a docker container, which is quite easy and very fast, this means you won't have to set up all the needed services for the bot, such as the postgresql database and the bot will run for you automatically. All you need to do is install docker. Run it as a service and use `docker-compose up` within the clonned project. You will need to have `BOT_TOKEN` environment variable set, with your bot token so that the bot can connect to your discord application.

### Bare-bones installation

You can also run the bot without using docker at all, even though using docker is more convenient and easier, sometimes you might want to run directly, because you might not have enough resources to spin up whole containers or you simply don't want to install docker. Even though we recommend docker installation over bare-bones one, it is important to mention it too.

#### Setting up postgresql database

In order to prevent cluttering the README too much,
here's a link to official documentation regarding installation:
[Official PostgreSQL installation tutorial](https://www.tutorialspoint.com/postgresql/postgresql_environment.htm)
Note that the installation steps will differ depending on your operating system.
Make sure to only follow the installation steps specific to your operating system.

After you made a database and a user with some password for it. You can tell the bot about it using environmental variabls:

* `DATABASE_NAME="bot"` This is the name of your database
* `DATABASE_USER="bot"` This is the username (ideally this shouldn't be postgres directly, but it can be)
* `DATABASE_PASSWORD="bot"` This is the password associated with that user account
* `DATABASE_HOST="127.0.0.1"` This defaults to `127.0.0.1` (localhost), but if you are running the database remotely, you'll want to adjust this

#### Starting the bot

1. Clone the repository (or fork it if you want to make changes)
2. Install [**poetry**](https://python-poetry.org/) `pip install poetry`
3. Build the virtual enviroment from poetry.lock `poetry install`
4. Create `.env` file for your environmental variables with:
   * `BOT_TOKEN=[Your bot token]`, this is tells the bot how to connect to your discord application
   * `COMMAND_PREFIX=[Your prefix]`, this is optional and will default to `>>`, if you want different prefix, change this
   * Rest of the postgresql config, as shown in the postgresql section
5. Configure the settings (More about this in **Settings** section)
6. Run the bot `poetry run task start`

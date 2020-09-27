# Neutron Bot

[![mit](https://img.shields.io/badge/Licensed%20under-MIT-red.svg?style=flat-square)](./LICENSE)
![Python package](https://github.com/Codin-Nerds/Neutron-Bot/workflows/Python%20package/badge.svg)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python%203.8-ffe900.svg?longCache=true&style=flat-square&colorB=00a1ff&logo=python&logoColor=88889e)](https://www.python.org/)
[![Discord](https://img.shields.io/static/v1?label=The%20Codin'%20Nerds&logo=discord&message=%3E300%20members&color=%237289DA&logoColor=white)](https://discord.gg/Dhz9pM7)

## About the bot

Neutron is still in the early development stage so there aren't many features available yet but we're aiming to change that soon.

## Installation

If you want to run this bot on your own, you can simply follow this guide:

### Creating the bot on Discord

1. Create bot on Discord's [bot portal](https://discord.com/developers/applications/)
2. Make a **New Application**
3. Go to **Bot** settings and click on **Add Bot**
4. Give **Administrator** permission to bot
5. You will find your bot **TOKEN** there, it is important that you save it
6. Go to **OAuth2** and click bot, than add **Administrator** permissions
7. You can follow the link that will appear to add the bot to your discord server

### Setting up postgresql database

In order to prevent cluttering the README too much,
here's a link to official documentation regarding installation:
[Official PostgreSQL installation tutorial](https://www.tutorialspoint.com/postgresql/postgresql_environment.htm)
Note that the installation steps will differ depending on your operating system.
Make sure to only follow the installation steps specific to your operating system.

### Running bot

1. Clone the repository (or fork it if you want to make changes)
2. Install **pipenv** `pip install pipenv`
3. Build the virtual enviroment from Pipfile.lock `pipenv sync`
4. Create **.env** file with `BOT_TOKEN=[Your bot token]`
5. Configure the settings (More about this in **Settings** section)
6. Run the bot `pipenv run start`

### Docker

We will include the option to run the bot in a docker container soon, once we do, we'll make sure to include a step-by-step instruction on running it.

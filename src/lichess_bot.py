from discord.ext import commands
import requests  # need to also pip install "requests[security]"
from rating import *

TOKEN = open('/etc/lichessbottoken.txt').read()
client = commands.Bot(command_prefix='l!')


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))


@client.command()
async def help():
    """
    Show bot help (commands, etc)
    :return:
    """
    pass  # TODO: help command


@client.command()
async def commands():
    """
    Alias for help
    """
    await help()


@client.command(pass_context=True)
async def rating(context):
    message = context.message
    if message.author == client.user:
        return

    contents = message.content.split()
    param1 = contents[1]
    match = re.match(r'(?:https://)?(?:www\.)?lichess\.org/@/([\S]+)/?', param1)
    if match:
        url = match.string
        name = match.groups()[0]
    else:
        url = f'https://lichess.org/@/{param1}'
        name = param1

    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError:
        await message.channel.send("Sending too many GET requests to lichess, please wait a minute.")
        return

    if response.status_code == 404:
        await message.channel.send("I can't find any ratings for this user!")
        return

    if len(contents) == 2:  # !rating [name/url]
        await all_ratings(message, response, name)
    elif len(contents) == 3:  # !rating [name/url] [gamemode]
        gamemode = contents[2]
        await gamemode_rating(message, response, name, gamemode)


if __name__ == '__main__':
    client.run(TOKEN)

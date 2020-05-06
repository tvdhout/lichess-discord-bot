from discord.ext import commands
import requests  # need to also pip install "requests[security]"
from rating import *

TOKEN = open('/etc/lichessbottoken.txt').read()
PREFIX = '!'  # command prefix

client = commands.Bot(command_prefix=PREFIX)
client.remove_command('help')


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))


@client.command(pass_context=True)
async def commands(context):
    """
    Show list of commands
    """
    embed = discord.Embed(title=f"Commands", colour=0x00ffff)
    embed.add_field(name=f"Rating", value=f"\n{PREFIX}rating [username] --> show all ratings and average rating"
                                          f"\n{PREFIX}rating [username] [gamemode] --> show rating for a "
                                          f"particular gamemode", inline=False)

    await context.message.channel.send(embed=embed)


@client.command(pass_context=True)
async def help(context):
    """
    Alias for commands
    """
    await commands(context)


@client.command(pass_context=True)
async def rating(context):
    message = context.message
    if message.author == client.user:
        return

    contents = message.content.split()
    if len(contents) == 1:  # !rating
        await message.channel.send(f"'rating' usage:"
                                   f"\n{PREFIX}rating [username] --> show all ratings and average rating"
                                   f"\n{PREFIX}rating [username] [gamemode] --> show rating for a particular gamemode")
        return

    param1 = contents[1]
    match = re.match(r'(?:https://)?(?:www\.)?lichess\.org/@/([\S]+)/?', param1)
    if match:  # user provided a link to their lichess page
        url = match.string
        name = match.groups()[0]
    else:  # user provided their username
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

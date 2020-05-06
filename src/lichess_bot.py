import discord
from discord.ext import commands
import requests  # need to also pip install "requests[security]"
from bs4 import BeautifulSoup
import re
import numpy as np

TOKEN = open('/etc/lichessbottoken.txt').read()
client = commands.Bot(command_prefix='!')


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


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

    soup = BeautifulSoup(response.text, 'html.parser')
    ratings = soup.find_all('rating')

    if len(ratings) < 4:
        await message.channel.send("I can't find any ratings for this user!")
        return

    embed = discord.Embed(title=f"{name}'s ratings",
                          url=url,
                          )
    embed.set_thumbnail(url='https://images.prismic.io/lichess/5cfd2630-2a8f-4fa9-8f78-04c2d9f0e5fe_lichess-box-1024'
                            '.png')

    ratings_list = []
    provisional = 0
    for rating_tag in ratings[:4]:
        gamemode = rating_tag.find_parent('a').find('h3').string
        rating = rating_tag.find('strong').string
        n_games = rating_tag.find('span').string
        embed.add_field(name=gamemode, value=f'{rating} ({n_games})', inline=False)
        if rating.endswith('?'):
            provisional = 1
            rating = rating[:-1]
        ratings_list.append(int(rating))

    average_rating = np.mean(ratings_list)
    embed.add_field(name='Average rating', value=f'**{average_rating}{provisional*"?"}**', inline=False)

    if average_rating < 1000:
        embed.colour = 0x9b0046
    elif average_rating < 1200:
        embed.colour = 0x8841a7
    elif average_rating < 1400:
        embed.colour = 0x5d2377
    elif average_rating < 1600:
        embed.colour = 0x1b5281
    elif average_rating < 1800:
        embed.colour = 0x2b84d3
    elif average_rating < 2000:
        embed.colour = 0x22ffa3
    elif average_rating < 2200:
        embed.colour = 0x22ff11
    else:
        embed.colour = 0xdd6a1b

    await message.channel.send(embed=embed)

if __name__ == '__main__':
    client.run(TOKEN)

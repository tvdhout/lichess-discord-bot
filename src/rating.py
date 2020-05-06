from bs4 import BeautifulSoup
import requests
import discord
import numpy as np
import re


async def all_ratings(message: discord.message.Message, response: requests.Response, name: str,
                      avg_only: bool = False) -> None:
    """
    Show the ratings for each gamemode and the average rating over ['Bullet', 'Blitz', 'Rapid', 'Classical']
    :param message: user's message to reply to
    :param response: HTTP response from the GET request to lichess
    :param name: lichess username for which to check the rating
    :param avg_only: Only show the average rating over ['Bullet', 'Blitz', 'Rapid', 'Classical']
    :return: Show the embedded ratings
    """
    soup = BeautifulSoup(response.text, 'html.parser')
    ratings = soup.find_all('rating')  # ratings are stored in rating tags

    if len(ratings) < 4:  # need at least 4 ratings for the average (if not found, the username may be inactive)
        await message.channel.send("I can't find any ratings for this user!")
        return

    embed = discord.Embed(title=f"{name}'s ratings",
                          url=f'https://lichess.org/@/{name}',
                          colour=0x00ffff
                          )
    embed.set_thumbnail(url='https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master/media/lichesslogo.'
                            'png')

    ratings_list = list()
    average_gamemodes = ['Bullet', 'Blitz', 'Rapid', 'Classical']  # Over which gamemodes should we take an average
    provisional = False
    for rating_tag in ratings:
        strong_tag = rating_tag.find('strong')
        if strong_tag:  # valid rating tag with rating inside
            gamemode = rating_tag.find_parent('a').find('h3').string
            rating = strong_tag.string
            n_games = rating_tag.find('span').string

            if gamemode in average_gamemodes:  # count towards average
                if not avg_only:
                    embed.add_field(name=gamemode, value=f'**{rating}** ({n_games})', inline=True)
                if rating.endswith('?'):  # provisional rating
                    provisional = True
                    rating = rating[:-1]  # remove question mark to cast to int
                ratings_list.append(int(rating))
            else:
                if not avg_only:
                    embed.add_field(name=gamemode, value=f'{rating} ({n_games})', inline=True)

    average_rating = np.mean(ratings_list)
    embed.add_field(name='Average rating (Bullet, Blitz, Rapid, Classical)',
                    value=f'**{average_rating}{"?" if provisional else ""}**', inline=False)

    await message.channel.send(embed=embed)


async def gamemode_rating(message: discord.message.Message, response: requests.Response, name: str,
                          gamemode: str) -> None:
    """
    Show the rating of a given user in a particular gamemode
    :param message: user's message to reply to
    :param response: HTTP response from the GET request to lichess
    :param name: lichess username for which to check the rating
    :param gamemode: which rating to check
    :return: send the embedded message, return nothing
    """
    if gamemode.lower() == 'average':
        await all_ratings(message, response, name, avg_only=True)
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    h3 = soup.find('h3', text=re.compile(rf'^{gamemode}s?$', re.I))

    if h3 is None:
        await message.channel.send(f"I can't find {name}'s {gamemode} rating")
        return

    rating = h3.parent.find('rating').find('strong').string
    n_games = h3.parent.find('rating').find('span').string

    embed = discord.Embed(title=f"{name}'s rating",
                          url=f'https://lichess.org/@/{name}',
                          colour=0x00ffff
                          )
    embed.set_thumbnail(url='https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master/media/lichesslogo.'
                            'png')
    embed.add_field(name=h3.string, value=f'{rating} ({n_games})')

    await message.channel.send(embed=embed)

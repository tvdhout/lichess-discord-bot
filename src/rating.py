import discord
import numpy as np


async def all_ratings(message: discord.message.Message, user: dict, avg_only: bool = False) -> None:
    """
    Show the ratings for each gamemode and the average rating over ['Bullet', 'Blitz', 'Rapid', 'Classical']
    :param message: user's message to reply to
    :param user: lichess.api user object
    :param avg_only: Only show the average rating over ['Bullet', 'Blitz', 'Rapid', 'Classical']
    :return: Show the embedded ratings
    """
    embed = discord.Embed(title=f"{user['username']}'s {'average' if avg_only else ''} rating{'' if avg_only else 's'}",
                          url=f"https://lichess.org/@/{user['username']}",
                          colour=0x00ffff
                          )
    embed.set_thumbnail(url='https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master/media/lichesslogo.'
                            'png')

    ratings = user['perfs']
    normal_modes = ['bullet', 'blitz', 'rapid', 'classical']
    ratings_to_average = []
    average_weights = []
    average_provisional = False

    for mode in normal_modes:
        rating = ratings[mode]['rating']
        n_games = ratings[mode]['games']
        provisional = 'prov' in ratings[mode]
        ratings_to_average.append(ratings[mode]['rating'])
        average_weights.append(ratings[mode]['games'])
        if provisional:
            average_provisional = True

        if not avg_only:
            embed.add_field(name=mode.capitalize(), value=f"**{rating}{'?' * provisional}** ({n_games} games)",
                            inline=True)

    if not avg_only:
        for mode in ratings:
            if mode in normal_modes:
                continue
            embed.add_field(name=mode.capitalize(), value=f"{ratings[mode]['rating']}{'?' * ('prov' in ratings[mode])} "
                                                          f"({ratings[mode]['games']} "
                                                          f"{'puzzles' if mode == 'puzzle' else 'games'})",
                            inline=True)

    average_rating = int(np.average(ratings_to_average, weights=average_weights))
    embed.add_field(name='Average rating weighted by number of games (Bullet, Blitz, Rapid, Classical)',
                    value=f'**{average_rating}{"?" if average_provisional else ""}**', inline=False)

    await message.channel.send(embed=embed)


async def gamemode_rating(message: discord.message.Message, user: dict, gamemode: str) -> None:
    """
    Show the rating of a given user in a particular gamemode
    :param message: user's message to reply to
    :param user: lichess.api user object
    :param gamemode: which rating to check
    :return: send the embedded message, return nothing
    """
    if gamemode.lower() == 'average':
        await all_ratings(message, user, avg_only=True)
        return

    embed = discord.Embed(title=f"{user['username']}'s rating",
                          url=f"https://lichess.org/@/{user['username']}",
                          colour=0x00ffff
                          )
    embed.set_thumbnail(url='https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master/media/lichesslogo.'
                            'png')

    if gamemode.lower() in user['prefs']:
        element = user['prefs'][gamemode.lower()]
        embed.add_field(name=gamemode.capitalize(), value=f"{element['rating']}{'?' * ('prov' in element)} "
                                                          f"({element['games']}"
                                                          f"{'puzzles' if gamemode.lower() == 'puzzle' else 'games'})")
    else:
        embed.add_field(name='Error', value=f"I can't find {user['username']}'s {gamemode} rating.")

    await message.channel.send(embed=embed)

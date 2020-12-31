import discord
from discord.ext.commands import Context
import numpy as np
import lichess.api


async def all_ratings(context: Context, username: str, avg_only: bool = False) -> None:
    """
    Show the ratings for each gamemode and the average rating over ['Bullet', 'Blitz', 'Rapid', 'Classical']
    :param context: context in which to reply
    :param username: lichess username
    :param avg_only: Only show the average rating over ['Bullet', 'Blitz', 'Rapid', 'Classical']
    :return: Show the embedded ratings
    """
    try:
        user = lichess.api.user(username)
    except lichess.api.ApiHttpError:
        embed = discord.Embed(title=f"Rating command", colour=0x00ffff)
        embed.add_field(name="Username not found", value=f"{username} is not an active Lichess account.")
        await context.send(embed=embed)
        return

    embed = discord.Embed(title=f"{username}'s {'average' if avg_only else ''} rating{'' if avg_only else 's'}",
                          url=f"https://lichess.org/@/{username}",
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

    if sum(average_weights) == 0:
        average_weights = [1] * len(average_weights)
    average_rating = int(np.average(ratings_to_average, weights=average_weights))
    embed.add_field(name='Average rating weighted by number of games (Bullet, Blitz, Rapid, Classical)',
                    value=f'**{average_rating}{"?" if average_provisional else ""}**', inline=False)

    await context.send(embed=embed)


async def gamemode_rating(context: Context, username: str, gamemode: str) -> None:
    """
    Show the rating of a given user in a particular gamemode
    :param context: context to reply in
    :param username: lichess usename
    :param gamemode: which rating to check
    :return: send the embedded message, return nothing
    """
    try:
        user = lichess.api.user(username)
    except lichess.api.ApiHttpError:
        embed = discord.Embed(title=f"Rating command", colour=0x00ffff)
        embed.add_field(name="Username not found", value=f"{username} is not an active Lichess account.")
        await context.send(embed=embed)
        return

    if gamemode.lower() == 'average':
        await all_ratings(context, username, avg_only=True)
        return

    embed = discord.Embed(title=f"{username}'s rating",
                          url=f"https://lichess.org/@/{user['username']}",
                          colour=0x00ffff
                          )
    embed.set_thumbnail(url='https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master/media/lichesslogo.'
                            'png')

    if gamemode.lower() in user['perfs']:
        element = user['perfs'][gamemode.lower()]
        embed.add_field(name=gamemode.capitalize(), value=f"{element['rating']}{'?' * ('prov' in element)} "
                                                          f"({element['games']} "
                                                          f"{'puzzles' if gamemode.lower() == 'puzzle' else 'games'})")
    else:
        embed.add_field(name='Error', value=f"I can't find {user['username']}'s {gamemode} rating. The user may not "
                                            f"have played enough games in this mode, or the gamemode doesn't exist.")

    await context.send(embed=embed)

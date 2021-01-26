from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context
import numpy as np
import lichess.api

from LichessBot import LichessBot


class Ratings(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @commands.command(name='rating', aliases=['ratings'])
    async def rating(self, context):
        """
        Entrypoint for the rating command
        Usage:
        !rating [username] - Retrieves the rating for user in every gamemode, with an average
        !rating [username] [gamemode] - Retrieves the rating for user in a particular gamemode
        !rating [username] average - Retrieves the average rating over Bullet, Blitz, Rapid and Classical
        @param context: ~Context: The context of the command
        @return:
        """
        message = context.message
        contents = message.content.split()

        if len(contents) == 1:  # -rating
            await self.all_ratings(context)
            return

        username = contents[1]

        if len(contents) == 2:  # !rating [name/url]
            await self.all_ratings(context, username=username)
        elif len(contents) > 2:  # !rating [name/url] [gamemode]
            gamemode = contents[2]
            await self.gamemode_rating(context, gamemode=gamemode, username=username)

    async def all_ratings(self, context: Context, username: Optional[str] = None) -> None:
        """
        Show the ratings of a particular user in an embed.
        @param context: ~Context: The context of the command
        @param username: Optional[str]: Lichess username for which to look up the rating. If none, check if this discord
        user has a Lichess account connected to it.
        @return:
        """
        if username is None:
            discord_uid = str(context.message.author.id)
            try:
                cursor = self.client.connection.cursor(buffered=True)
                cursor.execute("SELECT LichessName FROM users WHERE DiscordUID = %s", (discord_uid,))
                username = cursor.fetchall()[0][0]
                self.client.connection.commit()
                cursor.close()
            except IndexError:
                embed = discord.Embed(title="Rating command", colour=0xff0000)
                embed.add_field(name="No username",
                                value=f"To use this command without giving a username, link your Discord profile to "
                                      f"your Lichess account using `{self.client.config.prefix}connect ["
                                      f"username]`.\nAlternatively, provide a lichess username with `"
                                      f"{self.client.config.prefix}rating [username]`.")
                await context.send(embed=embed)
                return

        try:
            user = lichess.api.user(username)
        except lichess.api.ApiHttpError:
            embed = discord.Embed(title=f"Rating command", colour=0xff0000)
            embed.add_field(name="Username not found", value=f"{username} is not an active Lichess account.")
            await context.send(embed=embed)
            return

        embed = discord.Embed(title=f"{username}'s ratings", url=f"https://lichess.org/@/{username}", colour=0x00ffff)
        embed.set_thumbnail(url='https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master/media'
                                '/lichesslogo.png')

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

            embed.add_field(name=mode.capitalize(), value=f"**{rating}{'?' * provisional}** ({n_games} games)",
                            inline=True)

        for mode in ratings:
            if mode in normal_modes:
                continue
            embed.add_field(name=mode.capitalize(),
                            value=f"{ratings[mode]['rating']}{'?' * ('prov' in ratings[mode])} "
                                  f"({ratings[mode]['games']} "
                                  f"{'puzzles' if mode == 'puzzle' else 'games'})",
                            inline=True)

        if sum(average_weights) == 0:
            average_weights = [1] * len(average_weights)
        average_rating = int(np.average(ratings_to_average, weights=average_weights))
        embed.add_field(name='Average rating weighted by number of games (Bullet, Blitz, Rapid, Classical)',
                        value=f'**{average_rating}{"?" if average_provisional else ""}**', inline=False)

        await context.send(embed=embed)

    async def gamemode_rating(self, context: Context, gamemode: str, username: Optional[str] = None) -> None:
        """
        Show the rating of a given user in a particular gamemode
        @param context:
        @param gamemode:
        @param username:
        @return:
        """
        try:
            user = lichess.api.user(username)
        except lichess.api.ApiHttpError:
            embed = discord.Embed(title=f"Rating command", colour=0xff0000)
            embed.add_field(name="Username not found", value=f"{username} is not an active Lichess account.")
            await context.send(embed=embed)
            return

        embed = discord.Embed(title=f"{username}'s rating",
                              url=f"https://lichess.org/@/{user['username']}",
                              colour=0x00ffff
                              )
        embed.set_thumbnail(url='https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master/media'
                                '/lichesslogo.png')

        if gamemode.lower() in user['perfs']:
            element = user['perfs'][gamemode.lower()]
            embed.add_field(name=gamemode.capitalize(),
                            value=f"{element['rating']}{'?' * ('prov' in element)} "
                                  f"({element['games']} "
                                  f"{'puzzles' if gamemode.lower() == 'puzzle' else 'games'})")
        else:
            embed.add_field(name='Error',
                            value=f"I can't find {user['username']}'s {gamemode} rating. The user may not "
                                  f"have played enough games in this mode, or the gamemode doesn't exist.")
            embed.colour = 0xff0000

        await context.send(embed=embed)


def setup(client: LichessBot):
    client.add_cog(Ratings(client))

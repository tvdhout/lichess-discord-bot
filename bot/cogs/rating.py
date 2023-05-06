import requests

import discord
from discord import app_commands
from discord.utils import MISSING
from discord.ext import commands
from sqlalchemy import select

from LichessBot import LichessBot
from database import User


class Rating(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @app_commands.command(
        name='rating',
        description='View your or someone else\'s Lichess ratings',
    )
    @app_commands.describe(lichess_user='Lichess username whose ratings to look up')
    async def rating(self, interaction: discord.Interaction, lichess_user: str = None):
        self.client.logger.debug('Called Rating.rating')
        user = None
        if lichess_user is None:
            async with self.client.Session() as session:
                user = (await session.execute(select(User).filter(User.discord_id == interaction.user.id))).scalar()
            if user is None:
                return await interaction.response.send_message('You have not connected a Lichess account. Use `/rating '
                                                               '[lichess_user]` to lookup someone\'s Lichess rating, '
                                                               'or use `/connect` to connect your Lichess account.')
            lichess_user = user.lichess_username
        resp = requests.get(f'https://lichess.org/api/user/{lichess_user}')
        if resp.status_code == 404:
            embed = discord.Embed(title=f"Rating", colour=0xcc7474)
            embed.add_field(name="Username not found", value=f"{lichess_user} is not an active Lichess account.")
            return await interaction.response.send_message(embed=embed)
        try:
            resp.raise_for_status()

        except requests.HTTPError:
            return await interaction.response.send_message(f'Something went wrong with the Lichess API. If this keeps '
                                                           f'happening, please report it on the support server: '
                                                           f'https://discord.gg/KdpvMD72CV')

        embed = discord.Embed(title=f"{lichess_user}'s ratings", url=f'https://lichess.org/@/{lichess_user}',
                              colour=0xdbd7ca)
        embed.set_thumbnail(url='https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master/media'
                                '/lichesslogo.png')

        ratings = resp.json()['perfs']
        for mode in ratings:
            try:
                embed.add_field(name=mode.capitalize(),
                                value=f"{ratings[mode]['rating']}{'?' * ('prov' in ratings[mode])} "
                                      f"({ratings[mode]['games']} "
                                      f"{'puzzles' if mode == 'puzzle' else 'games'})",
                                inline=True)
            except KeyError:
                try:
                    embed.add_field(name=f"Puzzle {mode} score",
                                    value=f"{ratings[mode]['score']} ({ratings[mode]['runs']} runs)",
                                    inline=True)
                except KeyError:
                    self.client.logger.error(f'Error in /rating, mode={mode}, lichess_user={lichess_user}')

        await interaction.response.send_message(embed=embed)

        if user is not None:
            await self.client.update_user_rating(lichess_username=user.lichess_username)


async def setup(client: LichessBot):
    await client.add_cog(Rating(client), guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Rating')

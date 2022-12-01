import random

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.utils import MISSING
from discord.ext import commands
from sqlalchemy import select

from LichessBot import LichessBot
from views import PlayChallengeView
from database import User, Game, Puzzle


class Play(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @app_commands.command(
        name='play',
        description='Play chess on discord',
    )
    @app_commands.describe(opponent='@tag your opponent, they will be invited.')
    @app_commands.describe(color='The color you will play as (default is random).')
    @app_commands.choices(color=[Choice(name='White', value='w'), Choice(name='Black', value='b'),
                                   Choice(name='Random', value='r')])
    async def play(self, interaction: discord.Interaction, opponent: discord.User, color: str = 'r'):
        self.client.logger.debug('Called Play.play')
        if opponent == interaction.user:
            return await interaction.response.send_message("You can't challenge yourself to a game! :zany_face:",
                                                           ephemeral=True,
                                                           delete_after=5)
        async with self.client.Session() as session:
            game = (await session.execute(select(Game).filter(Game.channel_id == interaction.channel_id))).scalar()
            if game is not None:  # Another game is ongoing in this channel / thread.
                in_thread = interaction.channel.type == discord.ChannelType.forum
                return await interaction.response.send_message('There is already an ongoing chess game in this ' +
                                                               'thread. Please use `/play` in the channel containing '
                                                               'this thread instead.' if in_thread else
                                                               'channel. Please try another channel or create '
                                                               'a thread in which to play.',
                                                               ephemeral=True,
                                                               delete_after=7)
            users = (await session.execute(select(User)
                                           .filter(User.discord_id.in_((opponent.id, interaction.user.id))))
                     ).scalars()

        lichess_usernames = {user.discord_id: f' ({user.lichess_username})' for user in users}
        as_white = color == 'w' or (color == 'r' and random.choice([True, False]))

        embed = discord.Embed(title=f'Hi *{opponent.display_name}*!', colour=0xff8d4b,
                              description=f'You have been challenged to a game of chess by {interaction.user.mention}!')
        embed.add_field(
            name=f'{interaction.user.display_name}'
                 f'{lu if (lu := lichess_usernames.get(interaction.user.id, None)) is not None else ""}'
                 f' vs. '
                 f'{opponent.display_name}'
                 f'{lu if (lu := lichess_usernames.get(opponent.id, None)) is not None else ""}' if as_white else
            f'{opponent.display_name}'
            f'{lu if (lu := lichess_usernames.get(opponent.id, None)) is not None else ""}'
            f' vs. '
            f'{interaction.user.display_name}'
            f'{lu if (lu := lichess_usernames.get(interaction.user.id, None)) is not None else ""}',
            value='– Time control: 5 minutes per move.\n'
                  f'– {str(interaction.user) if as_white else str(opponent)} plays as white.\n'
                  '– This invitation is valid for 10 minutes.')
        embed.set_footer(text=f'Only {opponent} can accept or decline this challenge.')
        return await interaction.response.send_message(f'{opponent.mention} - You are invited to play a game of '
                                                       f'Discord chess with {interaction.user.mention}',
                                                       embed=embed,
                                                       view=PlayChallengeView(sessionmaker=self.client.Session),
                                                       delete_after=600)

    @app_commands.command(
        name='move',
        description='Move a piece during a chess game',
    )
    @app_commands.describe(move='Your chess move in SAN or UCI notation')
    async def move(self, interaction: discord.Interaction, move: str):
        self.client.logger.debug('Called Play.move')
        await interaction.response.defer()
        async with self.client.Session() as session:
            game = (await session.execute(select(Game)
                                          .filter(Game.channel_id == interaction.channel.id))
                    ).scalar()
            if game is None:
                puzzle = (await session.execute(select(Puzzle)
                                                .filter(Puzzle.channel_id == interaction.channel.id))
                          ).scalar()
                return await interaction.followup.send(f'You are not currently playing a game of chess. ' +
                                                       f'Challenge someone with `/play`!' if puzzle is None else
                                                       f'It looks like you are solving a puzzle – please use `/answer` '
                                                       f'instead.',
                                                       ephemeral=True,
                                                       delete_after=5)
        # TODO


async def setup(client: LichessBot):
    await client.add_cog(Play(client), guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Play')

import os
import re

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.utils import MISSING
from discord.ext import commands
from sqlalchemy import select
import chess
from chess import svg
from cairosvg import svg2png

from LichessBot import LichessBot
from views import PlayChallengeView, GameView
from database import User, Game, ChannelPuzzle


class Play(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @app_commands.command(
        name='play',
        description='Play chess on discord',
    )
    @app_commands.describe(opponent='@tag your opponent, they will be invited.')
    @app_commands.describe(time='Time for each playing in minutes (default is 10).')
    @app_commands.describe(increment='Time increment after each move in seconds (default is 0).')
    @app_commands.describe(color='The color you will play as (default is random).')
    @app_commands.choices(color=[Choice(name='White', value='white'), Choice(name='Black', value='black'),
                                 Choice(name='Random', value='random')])
    async def play(self, interaction: discord.Interaction, opponent: discord.User, time: int = 10, increment: int = 0,
                   color: str = 'random'):
        self.client.logger.debug('Called Play.play')
        if opponent == interaction.user:
            return await interaction.response.send_message("You can't challenge yourself to a game! :pensive:",
                                                           ephemeral=True,
                                                           delete_after=5)
        if 0 > time > 120 or 0 > increment > 60:
            return await interaction.response.send_message("The time control must be between 0 and 120 minutes, "
                                                           "use 0 for no time limit. The increment must be between "
                                                           "0 and 60 seconds.",
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

        embed = discord.Embed(title=f'Hi *{opponent.display_name}*!', colour=0xff8d4b,
                              description=f'You have been challenged to a game of chess by {interaction.user.mention}!')
        embed.add_field(
            name=f'{interaction.user.display_name}'
                 f'{lu if (lu := lichess_usernames.get(interaction.user.id, None)) is not None else ""}'
                 f' vs. '
                 f'{opponent.display_name}'
                 f'{lu if (lu := lichess_usernames.get(opponent.id, None)) is not None else ""}' if color == 'white'
            else
            f'{opponent.display_name}'
            f'{lu if (lu := lichess_usernames.get(opponent.id, None)) is not None else ""}'
            f' vs. '
            f'{interaction.user.display_name}'
            f'{lu if (lu := lichess_usernames.get(interaction.user.id, None)) is not None else ""}',
            value=f'– Time control: {f"{time}m + {increment}s increment." if time != 0 else "no time limit."}\n'
                  f'– Your color is '
                  f'{"decided randomly" if color == "random" else "white" if color == "black" else "black"}.\n'
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
        async with self.client.Session() as session:
            game = (await session.execute(select(Game)
                                          .filter(Game.channel_id == interaction.channel.id))
                    ).scalar()
            if game is None:
                puzzle = (await session.execute(select(ChannelPuzzle)
                                                .filter(ChannelPuzzle.channel_id == interaction.channel.id))
                          ).scalar()
                return await interaction.response.send_message(f'You are not currently playing a game of chess. ' +
                                                               f'Challenge someone with `/play`!' if puzzle is None else
                                                               f'It looks like you are solving a puzzle – please use `/answer` '
                                                               f'instead.',
                                                               ephemeral=True,
                                                               delete_after=7)
        if interaction.user.id not in (game.white_player_id, game.black_player_id):
            return await interaction.response.send_message(f'You are not playing this game!',
                                                           ephemeral=True,
                                                           delete_after=4)
        board = chess.Board(game.fen)
        self.client.logger.debug(
            f'white turn: {board.turn}, your id: {interaction.user.id}, white id: {game.white_player_id}')
        if board.turn ^ (game.white_player_id == interaction.user.id):  # Not our player's turn (using XOR)
            return await interaction.response.send_message(f'It is your opponents turn!',
                                                           ephemeral=True,
                                                           delete_after=3)

        illegal_move = False
        try:
            move = board.parse_san(move)
            board.push(move)
        except ValueError:
            self.client.logger.debug(f'move {move} not legal SAN for board {board}')
            try:
                move = board.parse_uci(move)
                board.push(move)
            except ValueError:
                self.client.logger.debug(f'move {move} not legal UCI for board {board}')
                illegal_move = True

        # See if the move stripped to basics is a legal move, then play that move.
        if illegal_move:
            stripped_move = re.sub(r'[|#+x]', '', move.lower())
            self.client.logger.debug(f'legal moves: {board.legal_moves}')
            for legal_move in board.legal_moves:
                if stripped_move in (legal_move.uci(), re.sub(r'[|#+x]', '', board.san(legal_move).lower())):
                    board.push(legal_move)
                    move = legal_move
                    break
            else:
                return await interaction.response.send_message(f'{move} is not a legal move in this position.',
                                                               ephemeral=True,
                                                               delete_after=4)

        color = 'white' if board.turn else 'black'  # swap board orientation for other player

        image = chess.svg.board(board, lastmove=move, colors={'square light': '#f2d0a2', 'square dark': '#aa7249'},
                                flipped=(color == 'black'))

        svg2png(bytestring=str(image), write_to=f'/tmp/{interaction.channel_id}_game.png', parent_width=1000,
                parent_height=1000)
        embed = discord.Embed(title=f"Updated board ({color} to move)",
                              colour=0xeeeeee if color == 'white' else 0x000000)
        file = discord.File(f'/tmp/{interaction.channel_id}_game.png',
                            filename="board.png")  # load puzzle as Discord file
        embed.set_image(url="attachment://board.png")

        if os.path.exists(f'/tmp/{interaction.channel_id}_game.png'):
            os.remove(f'/tmp/{interaction.channel_id}_game.png')

        await interaction.response.send_message(embed=embed, file=file, view=GameView(sessionmaker=self.client.Session))

        with self.client.Session() as session:
            ...


async def setup(client: LichessBot):
    await client.add_cog(Play(client), guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Play')

import os
import discord
import cairosvg
import random

import sqlalchemy
from discord import app_commands
from discord.app_commands import Choice
from discord.utils import MISSING
from discord.ext import commands
import chess
from chess import svg

from LichessBot import LichessBot
from database import Puzzle, ChannelPuzzle, User
from views import HintView

THEMES: dict[str, str] = {'Middlegame': 'middlegame', 'Endgame': 'endgame', 'Short': 'short', 'One move': 'oneMove',
                          'Long': 'long', 'Very long': 'veryLong', 'Mate': 'mate', 'Mate in one': 'mateIn1',
                          'Mate in two': 'mateIn2', 'Crushing': 'crushing', 'Advantage': 'advantage', 'Fork': 'fork',
                          'Pin': 'pin', 'Hanging piece': 'hangingPiece', 'Master game': 'master',
                          'Deflection': 'deflection', 'Quiet move': 'quietMove', 'Kingside attack': 'kingsideAttack',
                          'Sacrifice': 'sacrifice', 'Discovered attack': 'discoveredAttack',
                          'Defensive move': 'defensiveMove', 'Advanced pawn': 'advancedPawn',
                          'Rook endgame': 'rookEndgame'}


class PuzzleCog(commands.GroupCog, name='puzzle'):
    def __init__(self, client: LichessBot):
        super().__init__()
        self.client = client

    async def show_puzzle(self, puzzle: Puzzle, interaction: discord.Interaction) -> None:
        # Compute puzzle state
        board = chess.Board(puzzle.fen)
        initial_move_uci = puzzle.moves.pop(0)
        move = board.parse_uci(initial_move_uci)
        initial_move_san = board.san(move)
        board.push(move)
        fen = board.fen()
        color = 'white' if ' w ' in fen else 'black'

        # Create board image
        image = chess.svg.board(board, lastmove=move, colors={'square light': '#f2d0a2', 'square dark': '#aa7249'},
                                flipped=(color == 'black'))
        cairosvg.svg2png(bytestring=str(image),
                         write_to=f'/tmp/{interaction.channel_id}.png',
                         parent_width=1000,
                         parent_height=1000)
        file = discord.File(f'/tmp/{interaction.channel_id}.png', filename="puzzle.png")

        # Create embed
        embed = discord.Embed(title=f"Find the best move for {color}!\n(puzzle ID: {puzzle.puzzle_id})",
                              url=f'https://lichess.org/training/{puzzle.puzzle_id}',
                              colour=0xeeeeee if color == 'white' else 0x000000
                              )
        embed.set_image(url="attachment://puzzle.png")
        embed.add_field(name=f"Answer with `/answer`",
                        value=f"Answer using SAN ({initial_move_san}) or UCI ({initial_move_uci}) notation\n"
                              f"Puzzle difficulty rating: ||**{puzzle.rating}**||")
        try:
            if interaction.channel.type in [discord.ChannelType.text, discord.ChannelType.forum]:
                # Create new thread for the puzzle
                channel = await interaction.channel.create_thread(
                    name=f"{interaction.user.display_name}'s puzzle",
                    type=discord.ChannelType.public_thread,
                    auto_archive_duration=1440,  # After 1 day
                    reason='New chess puzzle started')
                await interaction.followup.send(f'I have created a new thread for your puzzle: {channel.mention}',
                                                ephemeral=True)
            else:
                channel = interaction.channel
                await interaction.followup.send('Here\'s your puzzle!')
        except discord.Forbidden:
            channel = interaction.channel
            await interaction.followup.send('Here\'s your puzzle!... By the way, if I get the permissions '
                                            '`Create Public Threads`, `Send Messages in Threads`, '
                                            'and `Manage Threads` I can create a new thread for each puzzle!')

        await channel.send(file=file, embed=embed, view=HintView())

        # Add puzzle to channel_puzzles table
        with self.client.Session() as session:
            channel_puzzle = ChannelPuzzle(channel_id=channel.id,
                                           puzzle_id=puzzle.puzzle_id,
                                           moves=puzzle.moves,
                                           fen=fen)
            session.merge(channel_puzzle)
            session.commit()

        # Delete board image
        if os.path.exists(f'/tmp/{interaction.channel_id}.png'):
            os.remove(f'/tmp/{interaction.channel_id}.png')

    @app_commands.command(
        name='random',
        description='Get a random puzzle. Selects one near your rating after `/connect`'
    )
    async def rand(self, interaction: discord.Interaction):
        await interaction.response.defer()
        with self.client.Session() as session:
            user = session.query(User).filter(User.discord_id == interaction.user.id).first()
            if user is None:  # User has not connected their Lichess account, get a random puzzle
                puzzle = session.query(Puzzle)[random.randrange(self.client.total_nr_puzzles)]
                await self.show_puzzle(puzzle, interaction)
            else:  # User has connected their Lichess account, get a puzzle near their puzzle rating
                query = session.query(Puzzle).filter(sqlalchemy.and_(Puzzle.rating > (user.puzzle_rating - 100),
                                                                     Puzzle.rating < (user.puzzle_rating + 200)))
                try:
                    puzzle = query[random.randrange(query.count())]
                    await self.show_puzzle(puzzle, interaction)
                except ValueError:
                    await interaction.followup.send(f'I cannot find a puzzle with a rating near your puzzle rating '
                                                    f'({user.puzzle_rating})! Please try `/puzzle rating` instead, or '
                                                    f'`/disconnect` your lichess account to get completely random '
                                                    f'puzzles.')

    @app_commands.command(
        name='id',
        description='Get a puzzle by ID'
    )
    @app_commands.describe(puzzle_id='Puzzle ID as found on lichess')
    async def id(self, interaction: discord.Interaction, puzzle_id: str):
        await interaction.response.defer()
        with self.client.Session() as session:
            puzzle = session.query(Puzzle).filter(Puzzle.puzzle_id == puzzle_id).first()
        if puzzle is None:
            return await interaction.followup.send(f'I cannot find a puzzle with that ID!')

        await self.show_puzzle(puzzle, interaction)

    @app_commands.command(
        name='rating',
        description='Get a random puzzle between two ratings'
    )
    @app_commands.describe(rating_from='Lowest rating', rating_to='Highest rating')
    async def rating(self, interaction: discord.Interaction, rating_from: int, rating_to: int):
        if rating_from > rating_to:
            return await interaction.response.send_message(f'`rating_from` should be smaller than `rating_to`!')
        await interaction.response.defer()
        with self.client.Session() as session:
            query = session.query(Puzzle).filter(Puzzle.rating.between(rating_from, rating_to))  # .subquery()
            try:
                puzzle = query[random.randrange(query.count())]
                await self.show_puzzle(puzzle, interaction)
            except ValueError:
                await interaction.followup.send(f'I don\'t have any puzzle with a rating between {rating_from} and '
                                                f'{rating_to} :-(')

    @app_commands.command(
        name='theme',
        description='Get a random puzzle with a certain theme. Selects one near your rating after `/connect`'
    )
    @app_commands.describe(theme='The theme of the puzzle',
                           ignore_rating='Ignore your own puzzle rating when getting a puzzle with this theme')
    @app_commands.choices(theme=[Choice(name=k, value=v) for k, v in THEMES.items()])
    async def theme(self, interaction: discord.Interaction, theme: str, ignore_rating: bool = False):
        await interaction.response.defer()
        with self.client.Session() as session:
            puzzle_query = session.query(Puzzle).filter(Puzzle.themes.any(theme))
            user = session.query(User).filter(User.discord_id == interaction.user.id).first()
            if user is None or ignore_rating:  # User has not connected their Lichess account, get a random puzzle
                puzzle = puzzle_query[random.randrange(puzzle_query.count())]
                await self.show_puzzle(puzzle, interaction)
            else:  # User has connected their Lichess account, get a puzzle near their puzzle rating
                puzzle_query = puzzle_query.filter(Puzzle.rating.between((user.puzzle_rating - 150),
                                                                         (user.puzzle_rating + 300)))
                try:
                    puzzle = puzzle_query[random.randrange(puzzle_query.count())]
                    await self.show_puzzle(puzzle, interaction)
                except ValueError:
                    await interaction.followup.send(f'I cannot find a puzzle with the theme "{theme}" and a rating '
                                                    f'near your puzzle rating ({user.puzzle_rating})! Use the option '
                                                    f'`ignore_rating` to get a puzzle with this theme regardless of '
                                                    f'its rating.')


async def setup(client: LichessBot):
    await client.add_cog(PuzzleCog(client),
                         guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Puzzle')

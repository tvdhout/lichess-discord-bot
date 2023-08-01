import os

import cairosvg
import requests
import sqlalchemy
from sqlalchemy import select, func
import discord
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
    def __init__(self, client: LichessBot) -> None:
        super().__init__()
        self.client = client

    async def show_puzzle(self, puzzle: Puzzle, interaction: discord.Interaction) -> None:
        self.client.logger.debug('Called Puzzle.show_puzzle')
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

        perms = interaction.app_permissions
        channel = interaction.channel
        try:
            if interaction.channel.type in (discord.ChannelType.text, discord.ChannelType.forum):
                self.client.logger.debug('interaction.channel.type in (discord.ChannelType.text, discord.ChannelType.forum)')
                # Create new thread for the puzzle
                if perms.create_public_threads and perms.send_messages_in_threads:
                    self.client.logger.debug('perms.create_public_threads and perms.send_messages_in_threads')
                    channel = await interaction.channel.create_thread(
                        name=f"{interaction.user.display_name}'s puzzle",
                        type=discord.ChannelType.public_thread,
                        auto_archive_duration=1440,  # After 1 day
                        reason='New chess puzzle started')
                    await channel.send(file=file, embed=embed, view=HintView(sessionmaker=self.client.Session))
                    await interaction.followup.send(f'I have created a new thread for your puzzle: {channel.mention}',
                                                    ephemeral=True)
                else:
                    self.client.logger.debug('ELSE!!!')
                    resp = requests.Response()
                    resp.status = 403
                    await interaction.user.send("Hi! I don't have the permissions to create a public thread or send "
                                                "messages in threads where you just asked for a puzzle. Please inform "
                                                "the server moderators.")
                    # raise discord.Forbidden(response=resp, message='Not authorized to create a public thread or send '
                    #                                                'messages in threads.')
            else:
                self.client.logger.debug('Else in channel')
                await interaction.followup.send('Here\'s your puzzle!',
                                                file=file, embed=embed, view=HintView(sessionmaker=self.client.Session))
        except discord.Forbidden:
            await interaction.followup.send('Here\'s your puzzle!',
                                            file=file, embed=embed, view=HintView(sessionmaker=self.client.Session))

        # Add puzzle to channel_puzzles table
        async with self.client.Session() as session:
            async with session.begin():
                channel_puzzle = ChannelPuzzle(channel_id=channel.id,
                                               puzzle_id=puzzle.puzzle_id,
                                               moves=puzzle.moves,
                                               fen=fen)
                await session.merge(channel_puzzle)
            await session.commit()

        # Delete board image
        if os.path.exists(f'/tmp/{interaction.channel_id}.png'):
            os.remove(f'/tmp/{interaction.channel_id}.png')

    @app_commands.command(
        name='random',
        description='Get a random puzzle. Selects one near your rating after using /connect'
    )
    async def rand(self, interaction: discord.Interaction):
        self.client.logger.debug('Called Puzzle.rand')
        await interaction.response.defer()
        async with self.client.Session() as session:
            try:
                user = (await session.execute(select(User).filter(User.discord_id == interaction.user.id))).scalar()
                assert user is not None and user.puzzle_rating is not None
            # User has not connected their Lichess account or has no puzzle rating, get a random puzzle
            except AssertionError:
                count = await self.client.total_nr_puzzles
                puzzle = (await session.execute(select(Puzzle)
                                                .offset(func.floor(func.random() * count))
                                                .limit(1))).scalar()
            # User has connected their Lichess account, get a puzzle near their puzzle rating
            else:
                q = (select(Puzzle).filter(sqlalchemy.and_(Puzzle.rating > (user.puzzle_rating - 100),
                                                           Puzzle.rating < (user.puzzle_rating + 100))))
                count = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar()
                puzzle = (await session.execute(q.offset(func.floor(func.random() * count)).limit(1))).scalar()
                # No puzzle found within user's rating.
                if puzzle is None:
                    return await interaction.followup.send(
                        f'I cannot find a puzzle with a rating near your puzzle rating '
                        f'({user.puzzle_rating})! Please try `/puzzle rating` instead, or '
                        f'`/disconnect` your lichess account to get completely random '
                        f'puzzles.')
            await self.show_puzzle(puzzle, interaction)
        if user is not None:
            await self.client.update_user_rating(user.lichess_username)

    @app_commands.command(
        name='id',
        description='Get a puzzle by ID'
    )
    @app_commands.describe(puzzle_id='Puzzle ID as found on lichess')
    async def id(self, interaction: discord.Interaction, puzzle_id: str):
        self.client.logger.debug('Called Puzzle.id')
        await interaction.response.defer()
        async with self.client.Session() as session:
            puzzle = (await session.execute(select(Puzzle).filter(Puzzle.puzzle_id == puzzle_id))).scalar()
            if puzzle is None:
                return await interaction.followup.send(f'I cannot find a puzzle with that ID! '
                                                       f'Note that puzzle IDs are case-sensitive.')

        await self.show_puzzle(puzzle, interaction)

    @app_commands.command(
        name='rating',
        description='Get a random puzzle between two ratings'
    )
    @app_commands.describe(rating_from='Lowest rating', rating_to='Highest rating')
    async def rating(self, interaction: discord.Interaction, rating_from: int, rating_to: int):
        self.client.logger.debug('Called Puzzle.rating')
        if rating_from > rating_to:
            return await interaction.response.send_message(f'`rating_from` should be smaller than `rating_to`!', 
                                                           ephemeral=True)
        await interaction.response.defer()
        async with self.client.Session() as session:
            q = select(Puzzle).filter(sqlalchemy.and_(Puzzle.rating > rating_from, Puzzle.rating < rating_to))
            count = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar()
            puzzle = (await session.execute(q.offset(func.floor(func.random() * count)).limit(1))).scalar()
            if puzzle is None:
                await interaction.followup.send(f'There are no puzzles with a rating between {rating_from} and '
                                                f'{rating_to}.')
            else:
                await self.show_puzzle(puzzle, interaction)

    @app_commands.command(
        name='theme',
        description='Get a random puzzle with a certain theme. Selects one near your rating after using /connect'
    )
    @app_commands.describe(theme='The theme of the puzzle',
                           ignore_rating='Ignore your own puzzle rating when getting a puzzle with this theme')
    @app_commands.choices(theme=[Choice(name=k, value=v) for k, v in THEMES.items()])
    async def theme(self, interaction: discord.Interaction, theme: str, ignore_rating: bool = False):
        self.client.logger.debug('Called Puzzle.theme')
        await interaction.response.defer()
        async with self.client.Session() as session:
            q = select(Puzzle).filter(Puzzle.themes.any(theme))
            if not ignore_rating:
                user = (await session.execute(select(User).filter(User.discord_id == interaction.user.id))).scalar()
            # User has not connected their Lichess account or has no puzzle rating
            if ignore_rating or user is None or user.puzzle_rating is None:
                pass
            else:  # User has connected their Lichess account, get a puzzle near their puzzle rating
                q = q.filter(Puzzle.rating.between((user.puzzle_rating - 150), (user.puzzle_rating + 300)))

            count = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar()
            puzzle = (await session.execute(q.offset(func.floor(func.random() * count)).limit(1))).scalar()
            if puzzle is None:
                await interaction.followup.send(f'I cannot find a puzzle with the theme "{theme}" and a rating '
                                                f'near your puzzle rating ({user.puzzle_rating})! Use the option '
                                                f'`ignore_rating` to get a puzzle with this theme regardless of '
                                                f'its rating.')
            else:
                await self.show_puzzle(puzzle, interaction)
        await self.client.update_user_rating(user.lichess_username)


async def setup(client: LichessBot):
    await client.add_cog(PuzzleCog(client),
                         guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Puzzle')

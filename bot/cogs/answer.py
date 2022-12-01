import re

import discord
from discord import app_commands
from discord.utils import MISSING
from discord.ext import commands
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import chess

from LichessBot import LichessBot
from database import ChannelPuzzle
from views import UpdateBoardView, WrongAnswerView


class Answer(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @app_commands.command(
        name='answer',
        description='Give the best move in the current position (requires an active /puzzle)',
    )
    @app_commands.describe(answer='The best move in this position in SAN or UCI notation')
    async def answer(self, interaction: discord.Interaction, answer: str):
        self.client.logger.debug('Called Answer.answer')
        async with self.client.Session() as session:
            c_puzzle: ChannelPuzzle = (
                await session.execute(
                    select(ChannelPuzzle)
                    .filter(ChannelPuzzle.channel_id == interaction.channel_id)
                    .options(selectinload(ChannelPuzzle.puzzle)))
            ).scalar()
            if c_puzzle is None:
                return await interaction.response.send_message('There is no active puzzle in this channel! Start a '
                                                               'puzzle with any of the `/puzzle` commands',
                                                               ephemeral=True,
                                                               delete_after=7)
            await interaction.response.defer()
            moves = c_puzzle.moves
            board = chess.Board(c_puzzle.fen)
            correct_uci = moves.pop(0)
            correct_san = board.san(board.parse_uci(correct_uci))
            stripped_correct_san = re.sub(r'[|#+x]', '', correct_san.lower())
            stripped_answer = re.sub(r'[|#+x]', '', answer.lower())

            def answer_is_mate(answer: str) -> bool:
                try:
                    board.push_san(answer)
                except ValueError:
                    try:
                        board.push_uci(answer)
                    except ValueError:
                        return False
                if board.is_game_over() and not board.is_stalemate():
                    return True
                board.pop()
                return False

            embed = discord.Embed(title=f'Your answer is...')

            if stripped_answer in [correct_uci, stripped_correct_san]:
                embed.colour = 0x7ccc74
                if len(moves) == 0:  # Last step of the puzzle
                    embed.add_field(name="Correct!", value=f"Yes! The best move was {correct_san} (or {correct_uci}). "
                                                           f"You completed the puzzle! (difficulty rating "
                                                           f"{c_puzzle.puzzle.rating})")
                    await interaction.followup.send(embed=embed)
                    await session.delete(c_puzzle)
                else:  # Not the last step of the puzzle
                    board.push_uci(correct_uci)
                    reply_uci = moves.pop(0)
                    move = board.parse_uci(reply_uci)
                    reply_san = board.san(move)
                    board.push(move)

                    embed.add_field(name='Correct!',
                                    value=f'Yes! The best move was {correct_san} (or {correct_uci}). The opponent '
                                          f'responded with {reply_san}. Now what\'s the best move?')
                    await interaction.followup.send(embed=embed,
                                                    view=UpdateBoardView(sessionmaker=self.client.Session))

                    await session.execute(update(ChannelPuzzle)
                                          .where(ChannelPuzzle.channel_id == c_puzzle.channel_id)
                                          .values(moves=moves, fen=board.fen()))
                await session.commit()
            elif answer_is_mate(answer) or answer_is_mate(answer.capitalize()):  # Check if the answer is mate
                embed.add_field(name="Correct!", value=f"Yes! {correct_san} (or {correct_uci}) is checkmate! You "
                                                       f"completed the puzzle! (difficulty rating "
                                                       f"{c_puzzle.puzzle.rating})")
                await interaction.followup.send(embed=embed)
                await session.delete(c_puzzle)
                await session.commit()
            else:  # Incorrect
                embed.colour = 0xcc7474
                embed.add_field(name="Wrong!",
                                value=f"{answer} is not the best move :-( Try again or get a hint!")

                await interaction.followup.send(embed=embed,
                                                view=WrongAnswerView(sessionmaker=self.client.Session))


async def setup(client: LichessBot):
    await client.add_cog(Answer(client), guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Answer')

from typing import Optional
import discord
from discord.ext import commands
from discord.ext.commands import Context
import re
import os
import chess
from chess import svg
from cairosvg import svg2png

from LichessBot import LichessBot


class Puzzles(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @commands.command(name='puzzle')
    async def puzzle(self, context: Context):
        """
        Entrypoint of the puzzle command
        Usage:
        !puzzle - Shows a random puzzle
        !puzzle [id] - Shows a specific puzzle (https://lichess.org/training/[id])
        @param context: ~Context: The context of the command
        @return:
        """
        message = context.message
        if message.author == self.client.user:
            return
        contents = message.content.split()
        if len(contents) == 1:
            await self.show_puzzle(context)
            return
        prefix = re.escape(self.client.prfx(context))  # Escape any regex metacharacters in prefix
        match = re.match(rf'^{prefix}puzzle +\[?(\d+)]* *[ _\-] *\[?(\d+)]?$', message.content)
        if match is not None:  # -puzzle rating1 - rating2
            low = int(match.group(1))
            high = int(match.group(2))
            await self.puzzle_by_rating(context, low=low, high=high)
        elif len(contents) == 2:
            await self.show_puzzle(context, puzzle_id=contents[1])

    async def show_puzzle(self, context: Context, puzzle_id: Optional[str] = None) -> None:
        """
        Show a Lichess puzzle. If a puzzle ID is given, show that puzzle. If the user if connected, show a puzzle with
        a rating around their puzzle rating. Otherwise show a random puzzle.
        @param context: ~Context: The context of the command
        @param puzzle_id: Optional[str]: Optional puzzle ID
        @return:
        """
        cursor = self.client.connection.cursor(buffered=True)
        connected = True
        if puzzle_id is None:
            try:  # Try fetch a puzzle near the user's puzzle rating
                discord_uid = str(context.message.author.id)
                cursor.execute(f"SELECT Rating FROM users WHERE DiscordUid = %s", (discord_uid,))
                rating = cursor.fetchall()[0][0]  # raises IndexError if user does not exist in table
                if rating == -1:
                    raise ValueError
                # Random PuzzleId
                puzzle_query = "WITH filtered AS (SELECT * FROM puzzles WHERE Rating BETWEEN %s AND %s)  " \
                               "SELECT PuzzleId, FEN, Moves, Rating, Themes " \
                               "FROM filtered " \
                               "JOIN (SELECT CEIL(RAND() * (SELECT MAX(id) FROM filtered)) AS rand_id) " \
                               "AS tmp " \
                               "WHERE filtered.id >= tmp.rand_id " \
                               "ORDER BY filtered.id ASC LIMIT 1;"
                query_data = (rating-50, rating+100)
            except (IndexError, ValueError) as e:
                if isinstance(e, IndexError):
                    connected = False  # User has not connected their Lichess account
                # Grab a random puzzle efficiently
                puzzle_query = "SELECT PuzzleId, FEN, Moves, Rating, Themes " \
                               "FROM puzzles " \
                               "JOIN (SELECT CEIL(RAND() * (SELECT MAX(id) FROM puzzles)) AS rand_id) " \
                               "AS tmp " \
                               "WHERE puzzles.id >= tmp.rand_id " \
                               "LIMIT 1;"
                query_data = tuple()
            cursor.execute(puzzle_query, query_data)
            puzzle_id, fen, moves, rating, themes = cursor.fetchall()[0]
            moves = moves.split()
        else:
            get_puzzle = "SELECT FEN, Moves, Rating, Themes FROM puzzles WHERE BINARY PuzzleId = %s;"
            cursor.execute(get_puzzle, (puzzle_id,))
            try:
                fen, moves, rating, themes = cursor.fetchall()[0]
                moves = moves.split()
            except IndexError:
                embed = discord.Embed(title="Puzzle command", colour=0xff0000)
                embed.add_field(name=f"Oops!",
                                value=f"I can't find a puzzle with puzzle id **{puzzle_id}**.\n"
                                      f"Command usage:\n"
                                      f"`{self.client.prfx(context)}puzzle` → show a random puzzle, or one near your "
                                      f"puzzle rating when connected with `{self.client.prfx(context)}connect`\n"
                                      f"`{self.client.prfx(context)}puzzle [id]` → show a particular puzzle\n"
                                      f"`{self.client.prfx(context)}puzzle rating1-rating2` → show a random puzzle "
                                      f"with a rating between rating1 and rating2.")
                await context.send(embed=embed)
                return

        # Play the initial move that starts the puzzle
        board = chess.Board(fen)
        initial_move_uci = moves.pop(0)
        move = board.parse_uci(initial_move_uci)
        initial_move_san = board.san(move)
        board.push(move)
        fen = board.fen()
        color = 'white' if ' w ' in fen else 'black'

        # Create svg image from board
        image = svg.board(board, lastmove=move, colors={'square light': '#f2d0a2', 'square dark': '#aa7249'},
                          flipped=(color == 'black'))
        # Save puzzle image as png
        svg2png(bytestring=str(image), write_to=f'{self.client.config.base_dir}/media/puzzle.png', parent_width=1000,
                parent_height=1000)

        embed = discord.Embed(title=f"Find the best move for {color}!\n(puzzle ID: {puzzle_id})",
                              url=f'https://lichess.org/training/{puzzle_id}',
                              colour=0xeeeeee if color == 'white' else 0x000000
                              )

        puzzle = discord.File(f'{self.client.config.base_dir}/media/puzzle.png',
                              filename="puzzle.png")  # load puzzle as Discord file
        embed.set_image(url="attachment://puzzle.png")
        embed.add_field(name=f"Answer with `{self.client.prfx(context)}answer` / `{self.client.prfx(context)}a`",
                        value=f"Answer using SAN ({initial_move_san}) or UCI ({initial_move_uci}) notation\n"
                              f"Puzzle difficulty rating: ||**{rating}**||")

        if not connected:
            embed.add_field(name=f"Get relevant puzzles:",
                            value=f"Connect your Lichess account with `{self.client.prfx(context)}connect` to get "
                                  f"puzzles around your puzzle rating!")

        msg = await context.send(file=puzzle, embed=embed)  # send puzzle

        # Keep track of this puzzle in this channel.
        channel_puzzle = ("INSERT INTO channel_puzzles "
                          "(ChannelId, PuzzleId, Moves, FEN, MessageId) "
                          "VALUES (%s, %s, %s, %s, %s) "
                          "ON DUPLICATE KEY UPDATE PuzzleId = VALUES(PuzzleId), "
                          "Moves = VALUES(Moves), FEN = VALUES(FEN), MessageId = VALUES(MessageId)")
        data_puzzle = (str(context.message.channel.id), str(puzzle_id), ' '.join(moves), str(fen), str(msg.id))

        cursor.execute(channel_puzzle, data_puzzle)

        # Delete puzzle image
        os.remove(f'{self.client.config.base_dir}/media/puzzle.png')
        self.client.connection.commit()
        cursor.close()

    async def puzzle_by_rating(self, context: Context, low: int, high: int):
        """
        Show a puzzle in a specific rating range, when user uses -puzzle low-high
        @param context: ~Context: The context of the command
        @param low: int: lower bound for puzzle rating
        @param high: int: upper bound for puzzle rating
        @return:
        """
        cursor = self.client.connection.cursor(buffered=True)
        if low > high:
            low, high = high, low

        puzzle_query = "WITH filtered AS (SELECT * FROM puzzles WHERE Rating BETWEEN %s AND %s)  " \
                       "SELECT PuzzleId " \
                       "FROM filtered " \
                       "JOIN (SELECT CEIL(RAND() * (SELECT MAX(id) FROM filtered)) AS rand_id) " \
                       "AS tmp " \
                       "WHERE filtered.id >= tmp.rand_id " \
                       "ORDER BY filtered.id ASC  LIMIT 1;"
        cursor.execute(puzzle_query, (low, high))
        try:
            puzzle_id = cursor.fetchall()[0][0]
        except IndexError:
            embed = discord.Embed(title="No puzzle found", color=0xff0000)
            embed.add_field(name="Error", value=f"There is no puzzle between ratings {low} and {high}!")
            await context.send(embed=embed)
            return

        self.client.connection.commit()
        cursor.close()
        await self.show_puzzle(context, puzzle_id=puzzle_id)


def setup(client: LichessBot):
    client.add_cog(Puzzles(client))
    client.logger.info("Sucessfully added cog: Puzzle")

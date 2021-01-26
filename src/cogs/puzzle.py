import discord
from discord.ext import commands
from discord.ext.commands import Context
import random
import re
import os
import chess
from chess import svg
from cairosvg import svg2png

from LichessBot import LichessBot


class Puzzles(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @commands.command(name='puzzle', aliases=['puzle'])
    async def puzzle(self, context: Context):
        """
        Entrypoint of the puzzle command

        _________
        Usage:
        !puzzle - Shows a random puzzle
        !puzzle [id] - Shows a specific puzzle (https://lichess.org/training/[id])
        """
        message = context.message
        if message.author == self.client.user:
            return
        prefix = '\\' + self.client.config.prefix if self.client.config.prefix in '*+()&^$[]{}?\\.' else \
            self.client.config.prefix  # escape prefix character to not break the regex
        match = re.match(rf'^{prefix}puzzle +\[?(\d+)]* *[ _\-] *\[?(\d+)]?$', message.content)
        contents = message.content.split()
        if match is not None:  # -puzzle rating1 - rating2
            low = int(match.group(1))
            high = int(match.group(2))
            await self.puzzle_by_rating(context, low=low, high=high)
        elif len(contents) == 2:
            await self.show_puzzle(context, puzzle_id=contents[1])
        else:
            await self.show_puzzle(context)

    @commands.command(name='answer', aliases=['a', 'asnwer', 'anwser'])
    async def answer(self, context):
        """
        Entrypoint for the answer command

        _________
        Usage:
        !answer [move] - Provide [move] as the best move for the position in the last shown puzzle. Provide moves in the
                         standard algebraic notation (Qxb7+, e4, Bxb2 etc). Check (+) and checkmate (#) notation is
                         optional
        """

        message = context.message
        if message.author == self.client.user:
            return

        contents = message.content.split()
        if len(contents) == 1:
            embed = discord.Embed(title=f"Answer command", colour=0x00ffff)
            embed.add_field(name="Answer a puzzle:", value=f"You can answer a puzzle by giving your answer in the SAN "
                                                           f"notation (e.g. Qxc5) or UCI notation (e.g. e2e4)\n "
                                                           f"`{self.client.config.prefix}answer [answer]`")
            await context.send(embed=embed)
        else:
            await self.answer_puzzle(context, answer=contents[1])

    @commands.command(name='bestmove')
    async def give_best_move(self, context: Context):
        """
        Give the best move for the last posted puzzle.
        Parameters
        ----------
        message - the command entered by the user, used as a context to know which channel to post the reply to
        """
        cursor = self.client.connection.cursor(buffered=True)

        get_puzzle = "SELECT puzzles.PuzzleId, Rating, channel_puzzles.Moves, channel_puzzles.FEN " \
                     "FROM channel_puzzles LEFT JOIN puzzles ON channel_puzzles.PuzzleId = puzzles.PuzzleId " \
                     "WHERE ChannelId = %s;"
        cursor.execute(get_puzzle, (str(context.channel.id),))

        try:
            puzzle_id, rating, moves, fen = cursor.fetchall()[0]
            moves = moves.split()
        except IndexError:
            embed = discord.Embed(title=f"No active puzzle!", colour=0xffff00)
            embed.add_field(name="Start a new puzzle",
                            value=f"To start a puzzle use the `{self.client.config.prefix}puzzle` command.\n"
                                  f"Use `{self.client.config.prefix}commands` for more options.")
            await context.send(embed=embed)
            return

        embed = discord.Embed(title=f"Answering puzzle ID: {puzzle_id}",
                              url=f'https://lichess.org/training/{puzzle_id}',
                              colour=0xffff00
                              )

        board = chess.Board(fen)
        move = board.parse_uci(moves.pop(0))
        san_move = board.san(move)
        board.push(move)

        if len(moves) > 1:  # More steps to come
            follow_up = board.parse_uci(moves.pop(0))
            follow_up_san = board.san(follow_up)  # To show the user
            board.push(follow_up)

            embed.add_field(name="Answer", value=f"The best move is ||{san_move}||. "
                                                 f"The opponent responded with ||{follow_up_san}||, now what's the best"
                                                 f" move?")
            await context.send(embed=embed)

            fen = board.fen()  # Updated FEN with the move played, to use in the next step
            update_query = ("UPDATE channel_puzzles "
                            "SET Moves = %s, FEN = %s "
                            "WHERE ChannelId = %s;")
            update_data = (' '.join(moves), str(fen), str(context.channel.id))
            cursor.execute(update_query, update_data)
        else:  # End of the puzzle
            embed.add_field(name="Answer", value=f"The best move is ||{san_move}||. That's the end of the puzzle! "
                                                 f"(difficulty rating {rating})")
            await context.send(embed=embed)
            delete_puzzle = ("DELETE FROM channel_puzzles "
                             "WHERE ChannelId = %s;")
            cursor.execute(delete_puzzle, (str(context.channel.id),))
        self.client.connection.commit()
        cursor.close()

    async def show_puzzle(self, context: Context, puzzle_id: str = '') -> None:
        """
        Show a puzzle
    
        Parameters
        ----------
        message - the command entered by the user, used as a context to know which channel to post the reply to
        cursor - mysql.connector cursor given by the connect decorator
        puzzle_id - by default an empty string, resulting in a random puzzle. People can enter a particular puzzle ID
        """
        cursor = self.client.connection.cursor(buffered=True)
        connected = True
        if puzzle_id == '':
            try:  # Try fetch a puzzle near the user's puzzle rating
                discord_uid = str(context.message.author.id)
                cursor.execute(f"SELECT Rating FROM users WHERE DiscordUid = %s", (discord_uid,))
                rating = cursor.fetchall()[0][0]  # raises IndexError if user does not exist in table
                if rating == -1:
                    raise ValueError
                puzzle_query = "SELECT PuzzleId FROM puzzles " \
                               "WHERE Rating BETWEEN %s AND %s " \
                               "ORDER BY RAND() LIMIT 1;"
                cursor.execute(puzzle_query, (rating - 100, rating + 200))
                puzzle_id = cursor.fetchall()[0][0]
            except (IndexError, ValueError) as e:
                if isinstance(e, IndexError):
                    connected = False  # User has not connected their Lichess account
                # Grab a random puzzle efficiently
                cursor.execute(f"SELECT MAX(id) FROM puzzles;")
                max_id = cursor.fetchall()[0][0]  # random puzzle ID
                random_id = random.randint(1, max_id)
                cursor.execute(f"SELECT PuzzleId FROM puzzles WHERE id = %s", (random_id,))
                puzzle_id = cursor.fetchall()[0][0]

        get_puzzle = "SELECT FEN, Moves, Rating, Themes FROM puzzles WHERE PuzzleId = %s;"

        cursor.execute(get_puzzle, (puzzle_id,))

        try:
            fen, moves, rating, themes = cursor.fetchall()[0]
            moves = moves.split()
        except IndexError:
            embed = discord.Embed(title="Puzzle command", colour=0xff0000)
            embed.add_field(name=f"Oops!",
                            value=f"I can't find a puzzle with puzzle id **{puzzle_id}**.\n"
                                  f"Command usage:\n"
                                  f"`{self.client.config.prefix}puzzle` → show a random puzzle, or one near your "
                                  f"puzzle rating when connected with `{self.client.config.prefix}connect`\n"
                                  f"`{self.client.config.prefix}puzzle [id]` → show a particular puzzle\n"
                                  f"`{self.client.config.prefix}puzzle rating1-rating2` → show a random puzzle with a "
                                  f"rating between rating1 and rating2.")
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
        embed.add_field(name=f"Answer with `{self.client.config.prefix}answer`",
                        value=f"Answer using SAN ({initial_move_san}) or UCI ({initial_move_uci}) notation\n"
                              f"Puzzle difficulty rating: ||**{rating}**||")

        if not connected:
            embed.add_field(name=f"Get relevant puzzles:",
                            value=f"Connect your Lichess account with `{self.client.config.prefix}connect` to get "
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
        cursor = self.client.connection.cursor(buffered=True)
        if low > high:
            low, high = high, low

        get_puzzle = "SELECT PuzzleId FROM puzzles WHERE Rating BETWEEN %s AND %s ORDER BY RAND() LIMIT 1"
        cursor.execute(get_puzzle, (low, high))
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

    async def answer_puzzle(self, context: Context, answer: str) -> None:
        """
        User can provide an answer to the last posted puzzle
    
        Parameters
        ----------
        message - the command entered by the user, used as a context to know which channel to post the reply to
        answer - the move the user provided
        """
        cursor = self.client.connection.cursor(buffered=True)
        # Fetch the active puzzle from the channel_puzzles table
        get_puzzle = "SELECT puzzles.PuzzleId, Rating, channel_puzzles.Moves, channel_puzzles.FEN, MessageId " \
                     "FROM channel_puzzles LEFT JOIN puzzles ON channel_puzzles.PuzzleId = puzzles.PuzzleId " \
                     "WHERE ChannelId = %s;"
        cursor.execute(get_puzzle, (str(context.channel.id),))

        try:
            puzzle_id, rating, moves, fen, message_id = cursor.fetchall()[0]
            moves = moves.split()
        except IndexError:
            embed = discord.Embed(title=f"No active puzzle!", colour=0xffff00)
            embed.add_field(name="Start a new puzzle",
                            value=f"To start a puzzle use the `{self.client.config.prefix}puzzle` command.\n"
                                  f"Use `{self.client.config.prefix}commands` for more options.")
            await context.send(embed=embed)
            return

        embed = discord.Embed(title=f"Answering puzzle ID: {puzzle_id}",
                              url=f'https://lichess.org/training/{puzzle_id}',
                              )

        board = chess.Board(fen)
        spoiler = '||' if answer.startswith('||') else ''
        stripped_answer = re.sub(r'[|#+x]', '', answer.lower())
        correct_uci = moves[0]
        correct_san = board.san(board.parse_uci(correct_uci))
        stripped_correct_san = re.sub(r'[|#+x]', '', correct_san.lower())

        # If the given answer is any checkmating move, it is correct no matter what the puzzle move is.
        def is_answer_mate(a: str, notation: str = 'san') -> bool:
            try:
                if notation == 'san':
                    board.push_san(a)
                else:
                    board.push_uci(a)
                if board.is_game_over():
                    return True
                board.pop()
                return False
            except ValueError:  # invalid move
                return False

        if is_answer_mate(answer) or is_answer_mate(answer, notation='uci') or is_answer_mate(answer.capitalize()):
            embed.colour = 0x00ff00
            embed.add_field(name="Correct!", value=f"Yes, {spoiler + answer + spoiler} is checkmate! "
                                                   f"You completed the puzzle! (difficulty rating {rating})")
            await context.send(embed=embed)
            # Puzzle is done, remove entry from channel_puzzles
            delete_puzzle = ("DELETE FROM channel_puzzles "
                             "WHERE ChannelId = %s;")
            cursor.execute(delete_puzzle, (str(context.channel.id),))
            return

        if stripped_answer in [correct_uci, stripped_correct_san]:  # Correct answer
            if len(moves) == 1:  # Last step in puzzle
                embed.colour = 0x00ff00
                embed.add_field(name="Correct!", value=f"Yes! The best move was {spoiler + correct_san + spoiler}. "
                                                       f"You completed the puzzle! (difficulty rating {rating})")
                await context.send(embed=embed)
                delete_puzzle = ("DELETE FROM channel_puzzles "
                                 "WHERE ChannelId = %s;")
                cursor.execute(delete_puzzle, (str(context.channel.id),))
                return
            else:  # Not the last step in puzzle
                # Apply the correct move + opponent's follow up to the chess.Board
                moves.pop(0)
                board.push(board.parse_uci(correct_uci))

                reply_uci = moves.pop(0)
                move = board.parse_uci(reply_uci)
                reply_san = board.san(move)  # To show the user
                board.push(move)

                fen = board.fen()  # Get the FEN of the board with applied moves to use for the next answer

                embed.colour = 0x00ff00
                embed.add_field(name="Correct!",
                                value=f"Yes! The best move was {spoiler + correct_san + spoiler}. The opponent "
                                      f"responded with {spoiler + reply_san + spoiler}, "
                                      f"now what's the best move?")
                await context.send(embed=embed)

                # Update the moves list and FEN in the channel_puzzles table
                update_query = ("UPDATE channel_puzzles "
                                "SET Moves = %s, FEN = %s "
                                "WHERE ChannelId = %s;")
                update_data = (' '.join(moves), str(fen), str(context.message.channel.id))

                cursor.execute(update_query, update_data)
        else:  # Incorrect answer
            embed.colour = 0xff0000
            embed.add_field(name="Wrong!",
                            value=f"{answer} is not the best move. Try again using `{self.client.config.prefix}"
                                  f"answer` or get the answer with `{self.client.config.prefix}bestmove`")

            await context.send(embed=embed)

        self.client.connection.commit()
        cursor.close()


def setup(client: LichessBot):
    client.add_cog(Puzzles(client))

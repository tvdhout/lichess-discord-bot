from typing import Union
import discord
from discord import Member, User, Reaction, Embed, TextChannel
from discord.ext import commands
from discord.ext.commands import Context
import json
import re
import os
import chess
from chess import svg
from cairosvg import svg2png

from LichessBot import LichessBot


class Answers(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, member: Union[User, Member]):
        if member.id == self.client.user.id:  # Bot added reaction
            return
        if reaction.me:  # Bot has previously reacted with the same reaction
            if (emoji := reaction.emoji) == "❓":
                await self.show_hint(reaction.message.channel)
            elif (emoji := reaction.emoji) == "👀":
                await self.show_updated_board(reaction.message.channel)
            # remove bot's reaction to avoid spamming the reaction
            await reaction.message.remove_reaction(emoji=emoji, member=self.client.user)

    @commands.command(name='answer', aliases=['a', 'asnwer', 'anwser'])
    async def answer(self, context):
        """
        Entrypoint for the answer command
        Usage:
        !answer [move] - Provide [move] as the best move for the position in the last shown puzzle. Provide moves in the
                         standard algebraic notation (Qxb7+, e4, Bxb2 etc). Check (+) and checkmate (#) notation is
                         optional
        @param context: ~Context: The context of the command
        @return:
        """
        message = context.message
        if message.author == self.client.user:
            return

        contents = message.content.split()
        if len(contents) == 1:
            embed = discord.Embed(title=f"Answer command", colour=0x00ffff)
            embed.add_field(name="Answer a puzzle:", value=f"You can answer a puzzle by giving your answer in the SAN "
                                                           f"notation (e.g. Qxc5) or UCI notation (e.g. e2e4)\n "
                                                           f"`{self.client.prfx(context)}answer [answer]` or "
                                                           f"`{self.client.prfx(context)}a [answer]`")
            await context.send(embed=embed)
        else:
            await self.answer_puzzle(context, answer=" ".join(contents[1:]))

    @commands.command(name='bestmove')
    async def give_best_move(self, context: Context):
        """
        Give the best move to in the currently active puzzle in this channel.
        @param context: ~Context: The context of the command
        @return:
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
                            value=f"To start a puzzle use the `{self.client.prfx(context)}puzzle` command.\n"
                                  f"Use `{self.client.prfx(context)}commands` for more options.")
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
            await self.send_with_reaction(context, embed, message="Click the eyes reaction to show the updated board.",
                                          emoji="👀")

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

    async def answer_puzzle(self, context: Context, answer: str) -> None:
        """
        Parse an answer to the active puzzle in the current channel given with -answer [answer]
        @param context: ~Context: The context of the command
        @param answer: str: The given answer to the puzzle in SAN or UCI format
        @return:
        """
        cursor = self.client.connection.cursor(buffered=True)
        # Fetch the active puzzle from the channel_puzzles table
        get_puzzle = "SELECT puzzles.PuzzleId, Rating, channel_puzzles.Moves, channel_puzzles.FEN, MessageId " \
                     "FROM channel_puzzles LEFT JOIN puzzles ON BINARY channel_puzzles.PuzzleId = puzzles.PuzzleId " \
                     "WHERE ChannelId = %s;"
        cursor.execute(get_puzzle, (str(context.channel.id),))

        try:
            puzzle_id, rating, moves, fen, message_id = cursor.fetchall()[0]
            moves = moves.split()
        except IndexError:
            embed = discord.Embed(title=f"No active puzzle!", colour=0xffff00)
            embed.add_field(name="Start a new puzzle",
                            value=f"To start a puzzle use the `{self.client.prfx(context)}puzzle` command.\n"
                                  f"Use `{self.client.prfx(context)}commands` for more options.")
            await context.send(embed=embed)
            return

        embed = discord.Embed(title=f"Answering puzzle ID: {puzzle_id}",
                              url=f'https://lichess.org/training/{puzzle_id}',
                              )

        # Set up the puzzle using the chess library. Used to parse answers, and to create a puzzle screenshot.
        board = chess.Board(fen)
        spoiler = '||' if answer.startswith('||') else ''
        stripped_answer = re.sub(r'[ |#+x]', '', answer.lower())
        correct_uci = moves[0]
        correct_san = board.san(board.parse_uci(correct_uci))
        stripped_correct_san = re.sub(r'[|#+x]', '', correct_san.lower())

        def is_answer_mate(a: str, notation: str = 'san') -> bool:
            """
            Determine if a given answer is checkmate on the current board.
            @param a: str: The given answer
            @param notation: SAN or UCI notation of the answer
            @return: bool: checkmate or not
            """
            try:
                if notation == 'san':
                    board.push_san(a)
                else:
                    board.push_uci(a)
                if board.is_game_over() and not board.is_stalemate():
                    return True
                board.pop()
                return False
            except ValueError:  # invalid move
                return False

        if stripped_answer in [correct_uci, stripped_correct_san]:  # Correct answer as per the puzzle solution
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

                await self.send_with_reaction(context, embed,
                                              message="Click the eyes reaction to show the updated board.",
                                              emoji="👀")

                # Update the moves list and FEN in the channel_puzzles table
                update_query = ("UPDATE channel_puzzles "
                                "SET Moves = %s, FEN = %s "
                                "WHERE ChannelId = %s;")
                update_data = (' '.join(moves), str(fen), str(context.message.channel.id))

                cursor.execute(update_query, update_data)
        # Check if the given answer is mate: check the plain answer, check it in UCI notation, and capitalized
        elif is_answer_mate(answer) or is_answer_mate(answer, notation='uci') or is_answer_mate(answer.capitalize()):
            embed.colour = 0x00ff00
            embed.add_field(name="Correct!", value=f"Yes, {spoiler + answer + spoiler} is checkmate! "
                                                   f"You completed the puzzle! (difficulty rating {rating})")
            await context.send(embed=embed)
            # Puzzle is done, remove entry from channel_puzzles
            delete_puzzle = ("DELETE FROM channel_puzzles "
                             "WHERE ChannelId = %s;")
            cursor.execute(delete_puzzle, (str(context.channel.id),))
            return
        else:  # Incorrect answer
            embed.colour = 0xff0000
            embed.add_field(name="Wrong!",
                            value=f"{answer} is not the best move. Try again using `{self.client.prfx(context)}"
                                  f"answer` or get the answer with `{self.client.prfx(context)}bestmove`")

            await self.send_with_reaction(context, embed, message="Click the question mark to get a hint!", emoji="❓")

        self.client.connection.commit()
        cursor.close()

    async def show_updated_board(self, channel: TextChannel):
        cursor = self.client.connection.cursor(buffered=True)

        get_puzzle = "SELECT channel_puzzles.PuzzleId, puzzles.FEN, channel_puzzles.Moves, puzzles.Moves " \
                     "FROM channel_puzzles LEFT JOIN puzzles ON channel_puzzles.PuzzleId = puzzles.PuzzleId " \
                     "WHERE ChannelId = %s;"
        cursor.execute(get_puzzle, (str(channel.id),))

        try:
            puzzle_id, fen, moves, all_moves = cursor.fetchall()[0]
            moves = moves.split()
            all_moves = all_moves.split()
        except IndexError:
            return  # No active puzzle

        board = chess.Board(fen)
        played_moves_uci = all_moves[:-(len(moves))]
        move = None
        for m in played_moves_uci:
            move = board.parse_uci(m)
            board.push(move)

        color = 'black' if ' w ' in fen else 'white'  # Other way around in the original puzzle fen (before first play)

        image = svg.board(board, lastmove=move, colors={'square light': '#f2d0a2', 'square dark': '#aa7249'},
                          flipped=(color == 'black'))

        svg2png(bytestring=str(image), write_to=f'{self.client.config.base_dir}/media/board.png', parent_width=1000,
                parent_height=1000)

        embed = discord.Embed(title=f"Updated board ({color} to play)\n(puzzle ID: {puzzle_id})",
                              url=f'https://lichess.org/training/{puzzle_id}',
                              colour=0xeeeeee if color == 'white' else 0x000000)
        puzzle = discord.File(f'{self.client.config.base_dir}/media/board.png',
                              filename="board.png")  # load puzzle as Discord file
        embed.set_image(url="attachment://board.png")

        await channel.send(file=puzzle, embed=embed)

        # Delete puzzle image
        os.remove(f'{self.client.config.base_dir}/media/board.png')
        self.client.connection.commit()
        cursor.close()

    async def show_hint(self, channel: TextChannel):
        cursor = self.client.connection.cursor(buffered=True)

        get_puzzle = "SELECT c.PuzzleId, c.fen, puzzles.Themes, c.Moves " \
                     "FROM channel_puzzles AS c LEFT JOIN puzzles ON c.PuzzleId = puzzles.PuzzleId " \
                     "WHERE ChannelId = %s;"
        cursor.execute(get_puzzle, (str(channel.id),))

        try:
            puzzle_id, fen, themes, moves = cursor.fetchall()[0]
            moves = moves.split()
            with open(f"{self.client.config.base_dir}/src/themes.json", "r") as f:
                themes_dict = json.loads(f.read())
            themes = list(filter(None, [themes_dict.get(theme, None) for theme in themes.split()]))
        except IndexError:
            return  # No active puzzle

        board = chess.Board(fen)
        next_move_uci = moves[0]
        move = board.parse_uci(next_move_uci)
        piece_to_move = chess.piece_name(board.piece_type_at(move.from_square)).capitalize()

        embed = Embed(title="Hints :bulb:", colour=0xff781f)
        embed.add_field(name="Piece to move", value=f"||{piece_to_move}||")
        embed.add_field(name="Puzzle themes", value="||"+", ".join(themes)+"||", inline=False)
        await channel.send(embed=embed)

    @staticmethod
    async def send_with_reaction(context: Context, embed: Embed, message: str, emoji: str):
        if isinstance(context.channel, discord.channel.DMChannel):
            await context.send(embed=embed)
            return
        react_permission = context.channel.permissions_for(context.guild.me).add_reactions
        if react_permission:
            embed.set_footer(text=message)
        else:
            embed.set_footer(text="I need the 'add reactions' permission for enhanced functionality!",
                             icon_url="https://raw.githubusercontent.com/tvdhout/Lichess-discord-bot/master"
                                      "/media/exclam.png")
        msg = await context.send(embed=embed)
        if react_permission:
            await msg.add_reaction(emoji)


def setup(client: LichessBot):
    client.add_cog(Answers(client))
    client.logger.info("Sucessfully added cog: Answer")

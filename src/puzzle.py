import discord
from discord.ext.commands import Context
import mysql.connector

import random

import re
import os
from typing import Optional

from config import PREFIX, BASE_DIR
from urllib.error import HTTPError
import chess
from chess import svg
# from cairosvg import svg2png
# https://gyazo.com/19e13e2459f92dd4e7b9cee749cb5982


async def show_puzzle(context: Context, puzzle_id: str = '') -> None:
    """
    Show a puzzle

    Parameters
    ----------
    message - the command entered by the user, used as a context to know which channel to post the reply to
    puzzle_id - by default an empty string, resulting in a random puzzle. People can also enter a particular puzzle ID
    """

    try:  # Connect to database
        connection = mysql.connector.connect(user='thijs',
                                             host='localhost',
                                             database='lichess')
    except mysql.connector.Error:
        await context.send("Oops! I can't connect to the puzzle database. This might be because I am working on the "
                           "database. If the problem persists, please let me know by filing an issue at "
                           "https://github.com/tvdhout/Lichess-discord-bot/issues or post in the bot support server: "
                           "https://discord.gg/xCpCRsp")
        return

    cursor = connection.cursor(buffered=True)

    if puzzle_id == '':
        cursor.execute(f"SELECT PuzzleId from puzzles ORDER BY RAND() LIMIT 1;")
        puzzle_id = cursor.fetchall()[0][0]  # random puzzle ID

    get_puzzle = f"SELECT (FEN, Moves, Rating, Themes) FROM puzzles WHERE PuzzleId = {puzzle_id};"

    cursor.execute(get_puzzle)

    try:
        FEN, moves, rating, themes = cursor.fetchall()[0]
    except IndexError:
        embed = discord.Embed(colour=0x00ffff)
        embed.add_field(name=f"Oops!", value=f"I can't find a puzzle with puzzle id '{puzzle_id}.'\n"
                                             f"Command usage:\n"
                                             f"`{PREFIX}puzzle` -> show a random puzzle\n"
                                             f"`{PREFIX}puzzle [id]` -> show a particular puzzle\n"
                                             f"`{PREFIX}puzzle rating1-rating2` -> show a random puzzle with a rating between "
                                             f"rating1 and rating2.")
        await context.send(embed=embed)
        return

    board = chess.Board(FEN)
    color = 'white' if board.turn else 'black'

    image = svg.board(board, colors={'square light': '#f2d0a2', 'square dark': '#aa7249'})
    # Save puzzle image
    svg2png(bytestring=str(image), write_to=f'{BASE_DIR}/media/puzzle.png', parent_width=1000, parent_height=1000)

    # Create embedding for the puzzle to sit in
    embed = discord.Embed(title=f"Find the best move for {color}!\n(puzzle {puzzle_id})",
                          url=f'https://lichess.org/training/{puzzle_id}',
                          colour=0x00ffff
                          )

    puzzle = discord.File(f'{BASE_DIR}/media/puzzle.png', filename="puzzle.png")  # load puzzle as Discord file
    embed.set_image(url="attachment://puzzle.png")
    embed.add_field(name=f"Answer with `{PREFIX}answer`",
                    value="Use the standard algebraic notation (Qxb7+), or UCI (b2c3)\n"
                          f"Puzzle difficulty rating: ||**{rating}**||")

    await context.send(file=puzzle, embed=embed)  # send puzzle

    # Set current puzzle as active for this channel.
    channel_puzzle = ("INSERT INTO channel_puzzles "
                      "(ChannelId, PuzzleId, Moves, FEN) "
                      "VALUES (%s, %s, %s, %s) "
                      "ON DUPLICATE KEY UPDATE PuzzleId = VALUES(PuzzleId)"
                      "Moves = VALUES(Moves), FEN = VALUES(FEN)")
    data_puzzle = (str(context.message.channel.id), str(puzzle_id), str(moves), str(FEN))

    cursor.execute(channel_puzzle, data_puzzle)
    connection.commit()

    # Purge puzzle images
    os.remove(f'{BASE_DIR}/media/puzzle.png')

    # Wrap up
    cursor.close()
    connection.disconnect()


async def puzzle_by_rating(context: Context, low: int, high: int):
    if low > high:
        low, high = high, low
    try:  # Connect to database
        connection = mysql.connector.connect(user='thijs',
                                             host='localhost',
                                             database='lichess')
    except mysql.connector.Error as err:
        print(err)
        await context.send("Oops! I can't connect to the puzzle database. This might be because I am working on the "
                           "database. If the problem persists, please let me know by filing an issue at "
                           "https://github.com/tvdhout/Lichess-discord-bot/issues or post in the bot support server: "
                           "https://discord.gg/xCpCRsp")
        return

    cursor = connection.cursor(buffered=True)
    get_puzzle = f"SELECT PuzzleId FROM puzzles WHERE Rating BETWEEN {low} AND {high}"
    cursor.execute(get_puzzle)
    try:
        puzzle_id = random.choice(cursor.fetchall())[0]
    except IndexError:
        await context.send(f"I can't find a puzzle between ratings {low} and {high}!")
        return

    await show_puzzle(context, puzzle_id)

    cursor.close()
    connection.disconnect()


async def answer_puzzle(context: Context, answer: str) -> None:
    """
    User can provide an answer to the last posted puzzle

    Parameters
    ----------
    message - the command entered by the user, used as a context to know which channel to post the reply to
    answer - the move the user provided
    """
    try:  # Connect to database
        connection = mysql.connector.connect(user='thijs',
                                             host='localhost',
                                             database='lichess')
    except mysql.connector.Error as err:
        print(err)
        await context.send("Oops! I can't connect to the puzzle database. This might be because I am working on the "
                           "database. If the problem persists, please let me know by filing an issue at "
                           "https://github.com/tvdhout/Lichess-discord-bot/issues or post in the bot support server: "
                           "https://discord.gg/xCpCRsp")
        return

    cursor = connection.cursor(buffered=True)

    get_puzzle = f"SELECT * FROM channel_puzzles WHERE ChannelId = {str(context.message.channel.id)};"
    cursor.execute(get_puzzle)
    try:
        _, puzzle_id, rating, moves, FEN = cursor.fetchall()[0]
    except IndexError:
        await context.send(f"There is no active puzzle in this channel! Check `{PREFIX}commands` for how to start a "
                           f"puzzle")
        return

    # Make sure the retrieved contents are lists, as expected, to prevent arbitrary code execution with eval().

    moves = moves.split()

    board = chess.Board(FEN)

    embed = discord.Embed(title=f"Answering puzzle {puzzle_id}",
                          url=f'https://lichess.org/training/{puzzle_id}',
                          colour=0x00ffff
                          )

    spoiler = '||' if answer.startswith('||') else ''
    if len(moves) == 0:
        embed.add_field(name="Oops!",
                        value="I'm sorry. I currently don't have the answers to a puzzle. Please try another "
                              f"`{PREFIX}puzzle`")
    elif re.sub(r'[|#+x]', '', answer.lower()) == re.sub(r'[#+x]', '', moves[0].lower()):
        if len(follow_ups) == 0:
            embed.add_field(name="Correct!", value=f"Yes! The best move was {spoiler + answers[0] + spoiler}. "
                                                   f"You completed the puzzle! (difficulty rating {puzzle_rating})")
        else:
            embed.add_field(name="Correct!",
                            value=f"Yes! The best move was {spoiler + answers[0] + spoiler}. The opponent "
                                  f"responded with {spoiler + follow_ups.pop(0) + spoiler}, "
                                  f"now what's the best move?")
        answers.pop(0)
    else:
        embed.add_field(name="Wrong!", value=f"{answer} is not the best move. Try again using `{PREFIX}"
                                             f"answer` or get the answer with `{PREFIX}bestmove`")

    await context.send(embed=embed)

    update_query = (f"UPDATE channel_puzzles "
                    f"SET answers = %s, follow_ups = %s "
                    f"WHERE channel_id = %s;")
    update_data = (str(answers), str(follow_ups), str(context.message.channel.id))

    cursor.execute(update_query, update_data)
    connection.commit()

    cursor.close()
    connection.disconnect()


async def give_best_move(context: Context) -> None:
    """
    Give the best move for the last posted puzzle.
    Parameters
    ----------
    message - the command entered by the user, used as a context to know which channel to post the reply to
    """
    try:  # Connect to database
        connection = mysql.connector.connect(user='thijs',
                                             host='localhost',
                                             database='lichess')
    except mysql.connector.Error as err:
        print(err)
        await context.send("Oops! I can't connect to the puzzle database. Please report this in the bot support "
                           "server: https://discord.gg/xCpCRsp or file an issue on GitHub.")
        return

    cursor = connection.cursor(buffered=True)

    get_puzzle = f"SELECT * FROM channel_puzzles WHERE channel_id = {str(context.message.channel.id)};"
    cursor.execute(get_puzzle)
    try:
        _, puzzle_id, puzzle_rating, answers, follow_ups = cursor.fetchall()[0]
    except IndexError:
        await context.send(f"There is no active puzzle in this channel! See {PREFIX}commands on how to start a "
                           f"puzzle")
        return

    if not (answers.startswith('[') and answers.endswith(']') and
            follow_ups.startswith('[') and follow_ups.endswith(']')):
        await context.send('Something went wrong loading this puzzle!')
        return

    answers = eval(answers)  # string representation to list
    follow_ups = eval(follow_ups)  # string representation to list

    embed = discord.Embed(title=f"Answering puzzle {puzzle_id}",
                          url=f'https://lichess.org/training/{puzzle_id}',
                          colour=0x00ffff
                          )
    if len(answers) == 0:
        embed.add_field(name="Oops!",
                        value="I'm sorry. I currently don't have the answers to a puzzle. Please try another "
                              f"{PREFIX}puzzle")
    elif len(follow_ups) > 0:
        embed.add_field(name="Answer", value=f"The best move is ||{answers.pop(0)}||. "
                                             f"The opponent responded with ||{follow_ups.pop(0)}||, now what's the best"
                                             f" move?")
    else:
        embed.add_field(name="Answer", value=f"The best move is ||{answers.pop(0)}||. That's the end of the puzzle! "
                                             f"(difficulty rating {puzzle_rating})")

    await context.send(embed=embed)

    update_query = (f"UPDATE channel_puzzles "
                    f"SET answers = %s, follow_ups = %s "
                    f"WHERE channel_id = %s;")
    update_data = (str(answers), str(follow_ups), str(context.message.channel.id))
    cursor.execute(update_query, update_data)
    connection.commit()

    cursor.close()
    connection.disconnect()

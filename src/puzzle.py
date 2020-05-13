import json
import discord

import requests
import wget
import random

import re
import os
from typing import Optional

from config import PREFIX, BASE_DIR
from urllib.error import HTTPError

answers = []
follow_ups = []
_puzzle_id = None
puzzle_rating = None


async def show_puzzle(message: discord.message.Message, puzzle_id: Optional[str] = '') -> None:
    """
    Show a puzzle

    Parameters
    ----------
    message - the command entered by the user, used as a context to know which channel to post the reply to
    puzzle_id - by default an empty string, resulting in a random puzzle. People can also enter a particular  puzzle ID
    """
    global _puzzle_id, answers, follow_ups, puzzle_rating

    if puzzle_id == '':
        puzzle_id = random.randint(1, 125272)  # random puzzle ID

    try:  # Download the puzzle image
        wget.download(f'https://lichess1.org/training/export/gif/thumbnail/{puzzle_id}.gif', f'{BASE_DIR}/media/puzzle.gif')
    except HTTPError:
        await message.channel.send(f"I can't find a puzzle with puzzle id '{puzzle_id}'")

    response = requests.get(f'https://lichess.org/training/{puzzle_id}')
    pattern = re.compile(r"lichess\.puzzle = (.*)</script><script nonce")  # find puzzle json string
    json_txt = pattern.findall(response.text)[0]
    js = json.loads(json_txt)
    color = js['data']['puzzle']['color']
    puzzle_rating = js['data']['puzzle']['rating']

    # Create embedding for the puzzle to sit in
    embed = discord.Embed(title=f"Find the best move for {color}!\n(puzzle {puzzle_id})",
                          url=f'https://lichess.org/training/{puzzle_id}',
                          colour=0x00ffff
                          )

    puzzle = discord.File(f'{BASE_DIR}/media/puzzle.gif', filename="puzzle.gif")  # load puzzle as Discord file
    embed.set_image(url="attachment://puzzle.gif")
    embed.add_field(name=f"Answer with {PREFIX}answer", value="Use the standard algebraic notation, e.g. Qxb7+\n"
                                                              f"Puzzle difficulty rating: ||{puzzle_rating}||")

    await message.channel.send(file=puzzle, embed=embed)  # send puzzle

    os.remove(f'{BASE_DIR}/media/puzzle.gif')

    answers = [(move := js['data']['puzzle']['branch'])['san']]
    follow_ups = []

    other = True
    while 'children' in move:
        if len(next_moves := move['children']) == 0:
            break
        move = next_moves[0]
        if other:
            follow_ups.append(move['san'])
        else:
            answers.append(move['san'])
        other = not other


async def answer_puzzle(message: discord.message.Message, answer: str) -> None:
    """
    User can provide an answer to the last posted puzzle

    Parameters
    ----------
    message - the command entered by the user, used as a context to know which channel to post the reply to
    answer - the move the user provided
    """
    embed = discord.Embed(title=f"Answering puzzle {_puzzle_id}",
                          url=f'https://lichess.org/training/{_puzzle_id}',
                          colour=0x00ffff
                          )
    spoiler = '||' if answer.startswith('||') else ''
    if len(answers) == 0:
        embed.add_field(name="Oops!",
                        value="I'm sorry. I currently don't have the answers to a puzzle. Please try another "
                              f"{PREFIX}puzzle")
    elif re.sub(r'[|#+]', '', answer.lower()) == re.sub(r'[#+]', '', answers[0].lower()):
        if len(follow_ups) == 0:
            embed.add_field(name="Correct!", value=f"Yes! The best move was {spoiler+answers[0]+spoiler}. "
                                                   f"You completed the puzzle! (difficulty rating {puzzle_rating})")
        else:
            embed.add_field(name="Correct!", value=f"Yes! The best move was {spoiler+answers[0]+spoiler}. The opponent "
                                                   f"responded with {spoiler+follow_ups.pop(0)+spoiler}, "
                                                   f"now what's the best move?")
        answers.pop(0)
    else:
        embed.add_field(name="Wrong!", value=f"{answer} is not the best move. Try again using {PREFIX}"
                                             f"answer or get the answer with {PREFIX}bestmove")

    await message.channel.send(embed=embed)


async def give_best_move(message: discord.message.Message) -> None:
    """
    Give the best move for the last posted puzzle.
    Parameters
    ----------
    message - the command entered by the user, used as a context to know which channel to post the reply to
    """
    embed = discord.Embed(title=f"Answering puzzle {_puzzle_id}",
                          url=f'https://lichess.org/training/{_puzzle_id}',
                          colour=0x00ffff
                          )
    if len(answers) == 0:
        embed.add_field(name="Oops!",
                        value="I'm sorry. I currently don't have the answers to a puzzle. Please try another "
                              f"{PREFIX}puzzle")
    elif len(follow_ups) > 0:
        embed.add_field(name="Answer", value=f"The best move is ||{answers.pop(0)}||. "
                                             f"The opponent responded with ||{follow_ups.pop(0)}||, now what's the best"
                                             f"move?")
    else:
        embed.add_field(name="Answer", value=f"The best move is ||{answers.pop(0)}||. That's the end of the puzzle! "
                                             f"(difficulty rating {puzzle_rating})")

    await message.channel.send(embed=embed)

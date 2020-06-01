"""
Invite the bot to your server with the following URL
https://discord.com/api/oauth2/authorize?client_id=707287095911120968&permissions=52224&scope=bot
"""
import discord
import re
from discord.ext import commands
from discord.ext.commands import Context
import requests  # need to also pip install "requests[security]"
from rating import all_ratings, gamemode_rating
from puzzle import show_puzzle, answer_puzzle, give_best_move, puzzle_by_rating
# from config import PREFIX, TOKEN
from config_dev import PREFIX, TOKEN


client = commands.Bot(command_prefix=PREFIX)
client.remove_command('help')  # remove default help command


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))


@client.command(pass_context=True)
async def commands(context: Context):
    """
    Show list of commands

    _________
    Usage
    !commands
    """
    embed = discord.Embed(title=f"Commands", colour=0x00ffff)
    embed.add_field(name=f"About", value=f"{PREFIX}about --> Show information about this bot", inline=False)
    embed.add_field(name=f"Rating", value=f"{PREFIX}rating [username] --> show all ratings and average rating"
                                          f"\n{PREFIX}rating [username] [gamemode] --> show rating for a "
                                          f"particular gamemode", inline=False)
    embed.add_field(name=f"Puzzle", value=f"{PREFIX}puzzle --> show a random lichess puzzle to solve"
                                          f"\n{PREFIX}puzzle [puzzle_id] --> show a particular lichess puzzle\n"
                                          f"{PREFIX}puzzle [rating1]-[rating2] --> show a random puzzle with a rating "
                                          f"between rating1 and rating2",
                    inline=False)
    embed.add_field(name="Answering puzzles",
                    value=f'{PREFIX}answer [move] --> give your answer to the most recent puzzle. '
                          f'Use the standard algebraic notation like Qxb7+. You can give your answer in spoiler tags'
                          f'like this: {PREFIX}answer `||move||`\n'
                          f'{PREFIX}bestmove --> get the best move to play in the previous puzzle, you can continue '
                          f'the puzzle from the next move.')

    await context.send(embed=embed)


@client.command(pass_context=True)
async def help(context):
    """
    Alias for commands

    _________
    Usage
    !help
    """
    await commands(context)


@client.command(pass_context=True)
async def about(context):
    """
    Show information about this bot

    _________
    Usage:
    !about
    """
    embed = discord.Embed(title=f"Lichess Discord bot", colour=0x00ffff,
                          url='https://github.com/tvdhout/Lichess-discord-bot')
    embed.add_field(name="About me",
                    value=f"I am a bot created by @stockvis and I can obtain various lichess-related "
                          f"pieces of information for you. You can see how I work here: "
                          f"https://github.com/tvdhout/Lichess-discord-bot. Check out what I can do using "
                          f"{PREFIX}commands.")

    await context.send(embed=embed)


@client.command(pass_context=True)
async def rating(context):
    """
    Retrieve the ratings for a lichess user

    _________
    Usage:
    !rating [username / url to lichess page] - Retrieves the rating for user in every gamemode, with an average
    !rating [username / url] [gamemode] - Retrieves the rating for user in a particular gamemode
    !rating [username / url] average - Retrieves the average rating over Bullet, Blitz, Rapid and Classical
    """
    message = context.message
    if message.author == client.user:
        return

    contents = message.content.split()
    if len(contents) == 1:  # !rating
        await context.send(f"\n{PREFIX}rating [username] --> show all ratings and average rating"
                                   f"\n{PREFIX}rating [username] [gamemode] --> show rating for a particular gamemode")
        return

    param1 = contents[1]
    match = re.match(r'(?:https://)?(?:www\.)?lichess\.org/@/([\S]+)/?', param1)
    if match:  # user provided a link to their lichess page
        url = match.string
        name = match.groups()[0]
    else:  # user provided their username
        url = f'https://lichess.org/@/{param1}'
        name = param1

    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError:
        await context.send("Sending too many GET requests to lichess, please wait a minute.")
        return

    if response.status_code == 404:
        await context.send("I can't find any ratings for this user!")
        return

    if len(contents) == 2:  # !rating [name/url]
        await all_ratings(message, response, name)
    elif len(contents) > 2:  # !rating [name/url] [gamemode]
        gamemode = contents[2]
        await gamemode_rating(message, response, name, gamemode)


@client.command(pass_context=True)
async def puzzle(context: Context):
    """
    Show a lichess puzzle for people to solve

    _________
    Usage:
    !puzzle - Shows a random puzzle
    !puzzle [id] - Shows a specific puzzle (https://lichess.org/training/[id])
    """
    message = context.message
    if message.author == client.user:
        return
    prefix = '\\'+PREFIX if PREFIX in '*+()&^$[]{}\\.' else PREFIX  # escape prefix character to not break the regex
    match = re.match(rf'^{prefix}puzzle +(\d+) *[ _\-] *(\d+)$', message.content)
    contents = message.content.split()
    if match is not None:  # !puzzle [id]
        low = int(match.group(1))
        high = int(match.group(2))
        await puzzle_by_rating(context, low, high)
    elif len(contents) == 2:
        await show_puzzle(context, contents[1])
    else:
        await show_puzzle(context)


@client.command(pass_context=True)
async def answer(context):
    """
    User provides answers to a puzzle

    _________
    Usage:
    !answer [move] - Provide [move] as the best move for the position in the last shown puzzle. Provide moves in the
                     standard algebraic notation (Qxb7+, e4, Bxb2 etc). Check (+) and checkmate (#) notation is optional
    """
    message = context.message
    if message.author == client.user:
        return

    contents = message.content.split()
    if len(contents) == 1:
        await context.send(f"Give an answer to the most recent puzzle using {PREFIX}answer [move]\n"
                                           "Use the common algebraic notation like Qxb7, R1a5, d4, etc.")
    else:
        await answer_puzzle(context, contents[1])


@client.command(pass_context=True)
async def bestmove(context):
    """
    Give the best move for the last shown puzzle.

    _________
    Usage:
    !bestmove - Shows the best move for the position in the last shown puzzle. If the puzzle consists of multiple moves
                the user can continue with the next move.
    """
    await give_best_move(context)


if __name__ == '__main__':
    client.run(TOKEN)

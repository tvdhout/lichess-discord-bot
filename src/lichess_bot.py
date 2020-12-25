"""
Invite the bot to your server with the following URL
https://discord.com/api/oauth2/authorize?client_id=707287095911120968&permissions=52224&scope=bot
"""
import discord
import re
import dbl
import config_dev
from discord.ext import commands
from discord.ext.commands import Context
import lichess.api

from profile import show_profile
from rating import all_ratings, gamemode_rating
from puzzle import show_puzzle, answer_puzzle, give_best_move, puzzle_by_rating
from config import PREFIX, TOKEN, TOP_GG_TOKEN  # configuration files for stable bot
# from config_dev import PREFIX, TOKEN, TOP_GG_TOKEN  # configuration for development bot

client = commands.Bot(command_prefix=PREFIX)
client.remove_command('help')  # remove default help command


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    print("Bot id: ", client.user.id)


@client.command(pass_context=True)
async def commands(context: Context):
    """
    Show list of commands

    _________
    Usage
    !commands
    """
    embed = discord.Embed(title=f"Commands", colour=0x00ffff)
    embed.add_field(name=f"Support", value=f"For help, issues or suggestions, join the "
                                           f"[bot support server](https://discord.gg/xCpCRsp).", inline=False)
    embed.add_field(name=f"About", value=f"`{PREFIX}about` --> Show information about this bot", inline=False)
    embed.add_field(name=f"Rating", value=f"`{PREFIX}rating [username]` --> show all ratings and average rating"
                                          f"\n`{PREFIX}rating [username] [gamemode]` --> show rating for a "
                                          f"particular gamemode", inline=False)
    embed.add_field(name=f"Puzzle", value=f"`{PREFIX}puzzle` --> show a random lichess puzzle to solve"
                                          f"\n`{PREFIX}puzzle [puzzle_id]` --> show a particular lichess puzzle\n"
                                          f"`{PREFIX}puzzle [rating1]-[rating2]` --> "
                                          f"show a random puzzle with a rating between rating1 and rating2",
                    inline=False)
    embed.add_field(name="Answering puzzles",
                    value=f'`{PREFIX}answer [move]` --> give your answer to the most recent puzzle. '
                          f'Use the standard algebraic notation like Qxb7+. You can give your answer in spoiler tags '
                          f'like this: `{PREFIX}answer ||move||`\n'
                          f'`{PREFIX}bestmove` --> get the best move to play in the previous puzzle, you can continue '
                          f'the puzzle from the next move.', inline=False)
    embed.add_field(name="Profile",
                    value=f'`{PREFIX}profile [username]` --> show a lichess user profile.', inline=False)

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
                          f"pieces of information for you. You can see how I work "
                          f"[on the GitHub page](https://github.com/tvdhout/Lichess-discord-bot). "
                          f"You can invite me to your own server from "
                          f"[this page](https://top.gg/bot/707287095911120968). "
                          f"Check out what I can do using `{PREFIX}commands.` "
                          f"Any issues or suggestions can be posted in the "
                          f"[bot support server](https://discord.gg/xCpCRsp).")

    await context.send(embed=embed)


@client.command(pass_context=True)
async def rating(context):
    """
    Retrieve the ratings for a lichess user

    _________
    Usage:
    !rating [username] - Retrieves the rating for user in every gamemode, with an average
    !rating [username] [gamemode] - Retrieves the rating for user in a particular gamemode
    !rating [username] average - Retrieves the average rating over Bullet, Blitz, Rapid and Classical
    """
    message = context.message
    if message.author == client.user:
        return

    contents = message.content.split()
    if len(contents) == 1:  # !rating TODO: use linked profile
        await context.send(f"\n`{PREFIX}rating [username]` --> show all ratings and average rating"
                           f"\n`{PREFIX}rating [username] [gamemode]` --> show rating for a particular gamemode")
        return

    username = contents[1]
    try:
        user = lichess.api.user(username)
    except lichess.api.ApiHttpError:
        await message.channel.send("This username does not exist!")
        return

    if len(contents) == 2:  # !rating [name/url]
        await all_ratings(message, user)
    elif len(contents) > 2:  # !rating [name/url] [gamemode]
        gamemode = contents[2]
        await gamemode_rating(message, user, gamemode)


@client.command(pass_context=True)
async def puzzle(context: Context):
    """
    Show a lichess puzzle for people to solve

    _________
    Usage:
    !puzzle - Shows a random puzzle
    !puzzle [id] - Shows a specific puzzle (https://lichess.org/training/[id])
    """

    embed = discord.Embed(title=f"Puzzle system updated", colour=0x00ffff)
    embed.add_field(name="Temporarily out of Service",
                    value=f"The Lichess puzzle system was recently updated. The puzzle commands will be inactive "
                          f"until I have updated the bot to accomodate these changes. Thank you for your understanding.")

    await context.send(embed=embed)

    # TEMPORARY - FIXME

    # message = context.message
    # if message.author == client.user:
    #     return
    # prefix = '\\' + PREFIX if PREFIX in '*+()&^$[]{}\\.' else PREFIX  # escape prefix character to not break the regex
    # match = re.match(rf'^{prefix}puzzle +(\d+) *[ _\-] *(\d+)$', message.content)
    # contents = message.content.split()
    # if match is not None:  # !puzzle [id]
    #     low = int(match.group(1))
    #     high = int(match.group(2))
    #     await puzzle_by_rating(context, low, high)
    # elif len(contents) == 2:
    #     await show_puzzle(context, contents[1])
    # else:
    #     await show_puzzle(context)


@client.command(pass_context=True)
async def answer(context):
    """
    User provides answers to a puzzle

    _________
    Usage:
    !answer [move] - Provide [move] as the best move for the position in the last shown puzzle. Provide moves in the
                     standard algebraic notation (Qxb7+, e4, Bxb2 etc). Check (+) and checkmate (#) notation is optional
    """

    embed = discord.Embed(title=f"Puzzle system updated", colour=0x00ffff)
    embed.add_field(name="Temporarily out of Service",
                    value=f"The Lichess puzzle system was recently updated. The puzzle commands will be inactive "
                          f"until I have updated the bot to accomodate these changes. Thank you for your understanding.")

    await context.send(embed=embed)

    # TEMPORARY - FIXME

    # message = context.message
    # if message.author == client.user:
    #     return
    #
    # contents = message.content.split()
    # if len(contents) == 1:
    #     await context.send(f"Give an answer to the most recent puzzle using `{PREFIX}answer [move]` \n"
    #                        "Use the common algebraic notation like Qxb7, R1a5, d4, etc.")
    # else:
    #     await answer_puzzle(context, contents[1])


@client.command(pass_context=True)
async def bestmove(context):
    """
    Give the best move for the last shown puzzle.

    _________
    Usage:
    !bestmove - Shows the best move for the position in the last shown puzzle. If the puzzle consists of multiple moves
                the user can continue with the next move.
    """
    embed = discord.Embed(title=f"Puzzle system updated", colour=0x00ffff)
    embed.add_field(name="Temporarily out of Service",
                    value=f"The Lichess puzzle system was recently updated. The puzzle commands will be inactive "
                          f"until I have updated the bot to accomodate these changes. Thank you for your understanding.")

    await context.send(embed=embed)

    # await give_best_move(context)


@client.command()
async def profile(message, username):
    # TODO: optional username, use linked profile
    await show_profile(message, username)


class TopGG(discord.ext.commands.Cog):
    """Handles interactions with the top.gg API"""

    def __init__(self, bot):
        self.bot = bot
        self.token = TOP_GG_TOKEN
        self.dblpy = dbl.DBLClient(self.bot, self.token, autopost=True)

    async def on_guild_post(self):
        print("Server count posted successfully")


if __name__ == '__main__':
    # FIXME: update server count
    if PREFIX != config_dev.PREFIX:
        topgg_cog = TopGG(client)
        client.add_cog(topgg_cog)
    client.run(TOKEN)

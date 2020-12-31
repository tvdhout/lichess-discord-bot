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
    embed.add_field(name=f"About", value=f"`{PREFIX}about` →  Show information about this bot", inline=False)
    embed.add_field(name=f"Rating", value=f"`{PREFIX}rating [username]` →  show all ratings and average rating"
                                          f"\n`{PREFIX}rating [username] [gamemode]` →  show rating for a "
                                          f"particular gamemode", inline=False)
    embed.add_field(name=f"Puzzle", value=f"`{PREFIX}puzzle` →  show a random lichess puzzle to solve"
                                          f"\n`{PREFIX}puzzle [puzzle_id]` →  show a particular lichess puzzle\n"
                                          f"`{PREFIX}puzzle [rating1]-[rating2]` →  "
                                          f"show a random puzzle with a rating between rating1 and rating2",
                    inline=False)
    embed.add_field(name="Answering puzzles",
                    value=f'`{PREFIX}answer [move]` →  give your answer to the most recent puzzle. '
                          f'Use the standard algebraic notation like *Qxb7+* or UCI like *a1b2*. You can give your '
                          f'answer in spoiler tags like this: `{PREFIX}answer ||move||`\n'
                          f'`{PREFIX}bestmove` →  get the best move to play in the previous puzzle, you can continue '
                          f'the puzzle from the next move.', inline=False)
    embed.add_field(name="Profile",
                    value=f'`{PREFIX}profile [username]` →  show a lichess user profile.', inline=False)

    await context.send(embed=embed)


@client.command(pass_context=True)
async def help(context):
    """
    Alias for commands
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
    contents = message.content.split()

    if len(contents) == 1:  # -rating TODO: use linked profile
        embed = discord.Embed(title=f"Rating command", colour=0x00ffff)
        embed.add_field(name="Show your Lichess ratings:", value=f"\n`{PREFIX}rating [username]` --> show all "
                                                                 f"ratings and average rating\n`{PREFIX}rating ["
                                                                 f"username] [gamemode]` --> show rating for a "
                                                                 f"particular gamemode")
        await context.send(embed=embed)
        return

    username = contents[1]

    if len(contents) == 2:  # !rating [name/url]
        await all_ratings(context, username)
    elif len(contents) > 2:  # !rating [name/url] [gamemode]
        gamemode = contents[2]
        await gamemode_rating(context, username, gamemode)


@client.command(pass_context=True)
async def ratings(context):
    """
    Alias for rating
    """
    await rating(context)


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
    prefix = '\\' + PREFIX if PREFIX in '*+()&^$[]{}?\\.' else PREFIX  # escape prefix character to not break the regex
    match = re.match(rf'^{prefix}puzzle +\[?(\d+)]* *[ _\-] *\[?(\d+)]?$', message.content)
    contents = message.content.split()
    if match is not None:  # -puzzle [id]
        low = int(match.group(1))
        high = int(match.group(2))
        await puzzle_by_rating(context, low=low, high=high)
    elif len(contents) == 2:
        await show_puzzle(context, puzzle_id=contents[1])
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
        embed = discord.Embed(title=f"Answer command", colour=0x00ffff)
        embed.add_field(name="Answer a puzzle:", value=f"You can answer a puzzle by giving your answer in the SAN "
                                                       f"notation (e.g. Qxc5) or UCI notation (e.g. e2e4)\n "
                                                       f"`{PREFIX}answer [answer]`")
        await context.send(embed=embed)
    else:
        await answer_puzzle(context, answer=contents[1])


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


@client.command(pass_context=True)
async def profile(context):
    # TODO: optional username, use linked profile
    content = context.message.content.split()
    try:
        username = content[1]
    except IndexError:
        embed = discord.Embed(title=f"Profile command", colour=0x00ffff)
        embed.add_field(name="Show a user profile:", value=f"`{PREFIX}profile [username]`")
        await context.send(embed=embed)
        return
    await show_profile(context, username)


class TopGG(discord.ext.commands.Cog):
    """Handles interactions with the top.gg API"""

    def __init__(self, bot):
        self.bot = bot
        self.token = TOP_GG_TOKEN
        self.dblpy = dbl.DBLClient(self.bot, self.token, autopost=True)

    @discord.ext.commands.Cog.listener()
    async def on_guild_post(self):
        print("Server count posted successfully")


if __name__ == '__main__':
    # FIXME: update server count
    if PREFIX != config_dev.PREFIX:
        client.add_cog(TopGG(client))
    client.run(TOKEN)

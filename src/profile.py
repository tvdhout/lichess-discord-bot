import lichess.api
import discord
from discord.ext.commands import Context
from datetime import timedelta
import db_connection
from config import PREFIX


@db_connection.connect
async def show_profile(context: Context, cursor, username: str = None) -> None:

    if username is None:
        discord_uid = str(context.message.author.id)
        try:
            cursor.execute("SELECT LichessName FROM users WHERE DiscordUID = %s", (discord_uid,))
            username = cursor.fetchall()[0][0]
        except IndexError:
            embed = discord.Embed(title="Profile command", colour=0xff0000)
            embed.add_field(name="No username",
                            value="To use this command without giving a username, link your Discord profile to your "
                                  f"Lichess account using `{PREFIX}connect [username]`.\n"
                                  f"Alternatively, provide a lichess username with `{PREFIX}profile [username]`.")
            await context.send(embed=embed)
            return

    embed = discord.Embed(title=f"{username}'s Profile", colour=0x00ffff)
    try:
        user = lichess.api.user(username)
        embed.url = f'https://lichess.org/@/{username}'
        embed.title = f"{user['username']}'s Profile"
    except lichess.api.ApiHttpError:
        embed.colour = 0xff0000
        embed.add_field(name='Error', value='This lichess usename does not exist.')
        await context.send(embed=embed)
        return

    profile_contents = ''
    if 'profile' in user:
        profile = user['profile']
        if 'country' in profile:
            embed.set_thumbnail(url=f"https://lichess1.org/assets/images/flags/{user['profile']['country']}.png")

        if 'bio' in profile:
            profile_contents += f"*Bio:* {profile['bio']}\n\n"
        if 'fideRating' in profile:
            profile_contents += f"*FIDE rating:* {profile['fideRating']}\n"

    # Play time
    td = str(timedelta(seconds=user['playTime']['total']))
    days = td.split(',')[0].split(' ')[0] + ' days,' if len(td.split(',')) > 1 else ''
    hours = int(td.split(',')[-1].split(':')[0])
    minutes = int(td.split(',')[-1].split(':')[1])
    profile_contents += f"*Play time:* {days} {hours} hours and {minutes} minutes.\n"

    profile_contents += str(user['count']['all']) + ' games played.\n'
    profile_contents += str(user['nbFollowers']) + ' followers.\n'

    embed.add_field(name="Profile", value=profile_contents)

    if user['online']:
        if 'playing' in user:
            embed.add_field(name="Status", value=f"[Playing]({user['playing']})")
        else:
            embed.add_field(name="Status", value='Online')
    else:
        embed.add_field(name="Status", value='Offline')

    embed.add_field(name='Export games', value=f"[Download](https://lichess.org/api/games/user/{user['username']})",
                    inline=False)

    await context.send(embed=embed)


@db_connection.connect
async def link_profile(context: Context, cursor, username: str) -> None:
    username = username.replace('[', '').replace(']', '')  # for dummies
    author = context.message.author
    discord_uid = str(author.id)
    if len(username) > 20:
        username = username[:20]+"..."
    embed = discord.Embed(title=f"Connecting '{author.display_name}' to Lichess account '{username}'", colour=0x00ff00)

    try:
        user = lichess.api.user(username)
    except lichess.api.ApiHttpError:
        embed.colour = 0xff0000
        embed.add_field(name='Error', value='This lichess usename does not exist.')
        await context.send(embed=embed)
        return

    try:
        puzzle_rating = user['perfs']['puzzle']['rating']
    except KeyError:  # No puzzle rating found
        puzzle_rating = 1500  # Set default to 1500

    embed.add_field(name="Success!",
                    value=f"I connected {author.mention} to the Lichess account "
                          f"[{username}](https://lichess.org/@/{username}).",
                    inline=False)
    embed.add_field(name="Effect on commands:",
                    value=f"You can now use the `{PREFIX}rating` and `{PREFIX}profile` commands without giving your "
                          f"username in the command.\n`{PREFIX}puzzle` will now select puzzles near your puzzle "
                          f"rating! If you don't have a puzzle rating, you will still get random puzzles.",
                    inline=False)
    embed.add_field(name="Disconnect",
                    value=f"To disconnect your Discord account from your Lichess account use the \n`{PREFIX}disconnect`"
                          f" command.",
                    inline=False)

    await context.send(embed=embed)

    query = ("INSERT INTO users "
             "(DiscordUID, LichessName, Rating) "
             "VALUES (%s, %s, %s) "
             "ON DUPLICATE KEY UPDATE LichessName = VALUES(LichessName), Rating = VALUES(Rating)")
    cursor.execute(query, (str(discord_uid), str(username), int(puzzle_rating)))


@db_connection.connect
async def unlink_profile(context: Context, cursor):
    author = context.message.author
    discord_uid = str(author.id)
    embed = discord.Embed(title=f"Disconnecting '{author.display_name}'", colour=0x00ff00)

    query = "DELETE FROM users WHERE DiscordUID = %s"
    cursor.execute(query, (discord_uid,))
    n_rows = cursor.rowcount
    message = "You are no longer connected to a Lichess account" if n_rows == 1 else "You were not connected to a " \
                                                                                     "Lichess account."
    embed.add_field(name="Disconnected", value=message)

    await context.send(embed=embed)

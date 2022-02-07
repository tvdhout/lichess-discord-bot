from typing import Optional
import lichess.api
import discord
from discord.ext import commands
from discord.ext.commands import Context
from datetime import timedelta

from LichessBot import LichessBot


class Profile(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @commands.command(name="profile")
    async def profile(self, context: Context):
        """
        Entrypoint for the profile command. Shows a Lichess user profile
        @param context: ~Context: The context of the command
        @return:
        """
        content = context.message.content.split()
        try:
            username = content[1]
            await self.show_profile(context, username=username)
        except IndexError:
            await self.show_profile(context)

    @commands.command(name="connect")
    async def connect(self, context: Context):
        """
        Entrypoint for the connect command. Connect a discord user to a Lichess account.
        @param context: ~Context: The context of the command
        @return:
        """
        content = context.message.content.split()
        try:
            username = content[1]
            await self.link_profile(context, username=username)
        except IndexError:
            embed = discord.Embed(title=f"Connect command", colour=0xff0000)
            embed.add_field(name="Connect your Lichess account to get more relevant puzzles:",
                            value=f"`{self.client.prfx(context)}connect [username]`")
            await context.send(embed=embed)

    @commands.command(name="disconnect")
    async def disconnect(self, context: Context):
        """
        Entrypoint for the disconnect command. Disconnect the discord user from a linked Lichess account.
        @param context: ~Context: The context of the command
        @return:
        """
        await self.unlink_profile(context)

    async def show_profile(self, context: Context, username: Optional[str] = None) -> None:
        """
        Show the profile of a Lichess account in an embed.
        @param context: ~Context: The context of the command
        @param username: Optional[str]: The username for which to show the profile. If none, search for a connected
        Lichess account for this discord user.
        @return:
        """
        self.client.logger.info("Called show_profile")
        cursor = self.client.connection.cursor(buffered=True)
        if username is None:
            discord_uid = str(context.message.author.id)
            try:
                cursor.execute("SELECT LichessName FROM users WHERE DiscordUID = %s", (discord_uid,))
                username = cursor.fetchall()[0][0]
            except IndexError:
                embed = discord.Embed(title="Profile command", colour=0xff0000)
                embed.add_field(name="No username",
                                value=f"To use this command without giving a username, link your Discord profile to "
                                      f"your Lichess account using `{self.client.prfx(context)}connect [username]`.\n"
                                      f"Alternatively, provide a lichess username with "
                                      f"`{self.client.prfx(context)}profile [username]`.")
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
        # profile_contents += str(user['nbFollowers']) + ' followers.\n'  # Deprecated
    
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
        self.client.connection.commit()
        cursor.close()

    async def link_profile(self, context: Context, username: str) -> None:
        """
        Connect the discord user to a Lichess account.
        @param context: ~Context: The context of the command
        @param username: str: The Lichess account name to connect to the discord user issuing the command
        @return:
        """
        cursor = self.client.connection.cursor(buffered=True)
        username = username.replace('[', '').replace(']', '')  # for dummies
        author = context.message.author
        discord_uid = str(author.id)
        if len(username) > 20:
            username = username[:20]+"..."
        embed = discord.Embed(title=f"Connecting '{author.display_name}' to Lichess account '{username}'",
                              colour=0x00ff00)
    
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
            puzzle_rating = -1  # No rating
    
        embed.add_field(name="Success!",
                        value=f"I connected {author.mention} to the Lichess account "
                              f"[{username}](https://lichess.org/@/{username}).",
                        inline=False)
        embed.add_field(name="Effect on commands:",
                        value=f"You can now use the `{self.client.prfx(context)}rating` and "
                              f"`{self.client.prfx(context)}profile` commands without giving your username in the "
                              f"command.\n`{self.client.prfx(context)}puzzle` will now select puzzles near your puzzle "
                              f"rating! If you don't have a puzzle rating, you will still get random puzzles.",
                        inline=False)
        embed.add_field(name="Disconnect",
                        value=f"To disconnect your Discord account from your Lichess account use the \n"
                              f"`{self.client.prfx(context)}disconnect` command.",
                        inline=False)
    
        await context.send(embed=embed)
    
        query = ("INSERT INTO users "
                 "(DiscordUID, LichessName, Rating) "
                 "VALUES (%s, %s, %s) "
                 "ON DUPLICATE KEY UPDATE LichessName = VALUES(LichessName), Rating = VALUES(Rating)")
        cursor.execute(query, (str(discord_uid), str(username), int(puzzle_rating)))
        self.client.connection.commit()
        cursor.close()

    async def unlink_profile(self, context: Context):
        """
        Disconnect the discord user from any linked Lichess account
        @param context: ~Context: The context of the command
        @return:
        """
        cursor = self.client.connection.cursor(buffered=True)
        author = context.message.author
        discord_uid = str(author.id)
        embed = discord.Embed(title=f"Disconnecting '{author.display_name}'", colour=0x00ff00)
    
        query = "DELETE FROM users WHERE DiscordUID = %s"
        cursor.execute(query, (discord_uid,))
        n_rows = cursor.rowcount
        message = "You are no longer connected to a Lichess account" if n_rows == 1 else \
            "You were not connected to a Lichess account."
        embed.add_field(name="Disconnected", value=message)
    
        await context.send(embed=embed)
        self.client.connection.commit()
        cursor.close()


def setup(client: LichessBot):
    client.add_cog(Profile(client))
    client.logger.info("Sucessfully added cog: Profile")

import discord
from discord import app_commands
from discord.utils import MISSING
from discord.ext import commands
from sqlalchemy import select

from LichessBot import LichessBot
from views import PlayChallengeView
from database import User


class Play(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @app_commands.command(
        name='play',
        description='Play chess on discord',
    )
    @app_commands.describe(opponent='@tag your opponent, they will be invited.')
    async def play(self, interaction: discord.Interaction, opponent: discord.User):
        self.client.logger.debug('Called Play.play')
        async with self.client.Session() as session:
            users = (await session.execute(select(User)
                                           .filter(User.discord_id.in_((opponent.id, interaction.user.id))))).scalars()
        lichess_usernames = {user.discord_id: f' ({user.lichess_username})' for user in users}

        embed = discord.Embed(title=f'Hi *{opponent.display_name}*!', colour=0xff8d4b,
                              description=f'You have been challenged to a game of chess by {interaction.user.mention}!')
        embed.add_field(
            name=f'{interaction.user.display_name}'
                 f'{lu if (lu := lichess_usernames.get(interaction.user.id, None)) is not None else ""}'
                 f' vs '
                 f'{opponent.display_name}'
                 f'{lu if (lu := lichess_usernames.get(opponent.id, None)) is not None else ""}',
            value='Time control: 5 minutes per move.\nThis invitation is valid for 10 minutes.')
        embed.set_footer(text=f'Only {opponent} can accept or decline this challenge.')  # Used in PlayChallengeView!
        return await interaction.response.send_message(f'{opponent.mention} - You are invited to play a game of '
                                                       f'Discord chess with {interaction.user.mention}',
                                                       embed=embed,
                                                       view=PlayChallengeView(sessionmaker=self.client.Session),
                                                       delete_after=600)


async def setup(client: LichessBot):
    await client.add_cog(Play(client), guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Play')

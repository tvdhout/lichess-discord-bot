import os
import hashlib
import random
import string
from base64 import urlsafe_b64encode

import discord
from discord import app_commands
from discord.utils import MISSING
from discord.ext import commands
from sqlalchemy import select, delete

from LichessBot import LichessBot
from database import APIChallenge, User
from views import ConnectView


class Connect(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client
        self.base_url = (f'https://lichess.org/oauth'
                         f'?response_type=code'
                         f'&client_id={os.getenv("CONNECT_CLIENT_ID")}'
                         f'&redirect_uri={os.getenv("CONNECT_REDIRECT_URI")}'
                         f'&code_challenge_method=S256')

    @app_commands.command(
        name='connect',
        description='Connect your Lichess account to get personalized puzzles',
    )
    async def connect(self, interaction: discord.Interaction):
        self.client.logger.debug('Called Connect.connect')
        async with self.client.Session() as session:
            user = (await session.execute(select(User).filter(User.discord_id == 289163010835087360))).first()
            if user is not None:
                return await interaction.response.send_message(f'You already have connected a Lichess account '
                                                               f'({user[0].lichess_username}). To connect a different '
                                                               f'account, please first disconnect your current account '
                                                               f'using `/disconnect`',
                                                               ephemeral=True)
            code_verifier = ''.join(random.SystemRandom()
                                    .choice(string.ascii_lowercase + string.digits)
                                    for _ in range(64))
            code_challenge = (urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest())
                              .decode('utf-8').replace('=', ''))
            url = self.base_url + f'&code_challenge={code_challenge}&state={interaction.user.id}'

            await interaction.response.send_message(view=ConnectView(url), ephemeral=True)

            session.add(APIChallenge(discord_id=interaction.user.id,
                                     code_verifier=code_verifier))
            await session.commit()

    @app_commands.command(
        name='disconnect',
        description='Disconnect your Lichess account',
    )
    async def disconnect(self, interaction: discord.Interaction):
        self.client.logger.debug('Called Connect.disconnect')
        async with self.client.Session() as session:
            q = delete(User).where(User.discord_id == interaction.user.id)
            result = await session.execute(q)
            await session.commit()
        if result.rowcount > 0:
            await interaction.response.send_message('Lichess account succesfully disconnected and data deleted.',
                                                    ephemeral=True)
        else:
            await interaction.response.send_message('You have not connected a Lichess account.', ephemeral=True)


async def setup(client: LichessBot):
    await client.add_cog(Connect(client),
                         guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Connect')

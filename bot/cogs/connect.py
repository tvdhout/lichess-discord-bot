import os
import hashlib
import random
import string
from base64 import urlsafe_b64encode

import discord
from discord import app_commands
from discord.utils import MISSING
from discord.ext import commands

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
        with self.client.Session() as session:
            user = session.query(User).filter(User.discord_id == interaction.user.id).first()
            if user is not None:
                return await interaction.response.send_message(f'You already have connected a Lichess account '
                                                               f'({user.lichess_username}). To connect a different '
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

            session.merge(APIChallenge(discord_id=interaction.user.id,
                                       code_verifier=code_verifier))
            session.commit()

    @app_commands.command(
        name='disconnect',
        description='Disconnect your Lichess account',
    )
    async def disconnect(self, interaction: discord.Interaction):
        with self.client.Session() as session:
            n_deleted: int = session.query(User).filter(User.discord_id == interaction.user.id).delete()
            session.commit()
        if n_deleted > 0:
            await interaction.response.send_message('Lichess account succesfully disconnected and data deleted.',
                                                    ephemeral=True)
        else:
            await interaction.response.send_message('You have not connected a Lichess account.', ephemeral=True)


async def setup(client: LichessBot):
    await client.add_cog(Connect(client),
                         guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Connect')

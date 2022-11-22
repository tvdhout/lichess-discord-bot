import re

import requests
import discord
from discord import app_commands
from discord.utils import MISSING
from discord.ext import commands

from LichessBot import LichessBot


class About(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @app_commands.command(
        name='about',
        description='About this bot',
    )
    async def about(self, interaction: discord.Interaction):
        self.client.logger.debug('Called About.about')
        try:
            database_site = requests.get('https://database.lichess.org/#puzzles').content.decode('utf-8')
            n_puzzles = re.search(r'<strong>([\d,]+)</strong>', database_site).group(1)
        except (requests.RequestException, AttributeError):
            n_puzzles = '3 million'

        embed = discord.Embed(title='Lichess Discord Bot', color=0xdbd7ca,
                              url="https://github.com/tvdhout/lichess-discord-bot")
        embed.set_footer(text="Made by Thijs#9356",
                         icon_url="https://cdn.discordapp.com/avatars/289163010835087360/"
                                  "f54134557a6e3097fe3ffb8f6ba0cb8c.webp?size=128")
        embed.add_field(name='🤖 About this bot', value=f'The Lichess Bot enables you to solve Lichess\' {n_puzzles} '
                                                        f'puzzles in the Discord chat (try the different `/puzzle` '
                                                        f'commands). You can connect it to your Lichess account to '
                                                        f'get puzzles near your rating, and look up anyone\'s '
                                                        f'Lichess ratings and profile. The bot has recently been '
                                                        f'updated to interact exclusively through slash commands.',
                        inline=False)
        embed.add_field(name='🌐 Open source', value='The source code for this bot is publicly available. You can find '
                                                     'it on [GitHub](https://github.com/tvdhout/lichess-discord-bot).',
                        inline=False)
        embed.add_field(name='👍 Top.gg', value='If you enjoy the bot, you can upvote it, rate it, and leave a comment '
                                             'on [its top.gg page](https://top.gg/bot/707287095911120968). Top.gg is '
                                             'a website that lists many public Discord bots. Thanks!',
                        inline=False)
        embed.add_field(name='🦠 Support', value='Found a bug? Need help? Have some suggestions? Reach out to me on '
                                                 'the support [discord server](https://discord.gg/KdpvMD72CV)!',
                        inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(client: LichessBot):
    await client.add_cog(About(client), guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: About')

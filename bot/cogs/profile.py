from datetime import datetime, timedelta
import calendar

import aiohttp
import discord
from discord import app_commands
from discord.utils import MISSING
from discord.ext import commands
from sqlalchemy import select

from LichessBot import LichessBot
from database import User


class Profile(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @app_commands.command(
        name='profile',
        description='View your or someone else\'s Lichess profile',
    )
    @app_commands.describe(lichess_user='Lichess username whose profile to look up')
    async def profile(self, interaction: discord.Interaction, lichess_user: str = None):
        self.client.logger.debug('Called Profile.profile')
        if lichess_user is None:
            async with self.client.Session() as session:
                user = (await session.execute(select(User).filter(User.discord_id == interaction.user.id))).scalar()
            if user is None:
                return await interaction.response.send_message('You have not connected a Lichess account. Use `/rating '
                                                               '[lichess_user]` to lookup someone\'s Lichess profile, '
                                                               'or use `/connect` to connect your Lichess account.')
            lichess_user = user.lichess_username

        async with aiohttp.ClientSession() as web:
            async with web.get(url=f'https://lichess.org/api/user/{lichess_user}',
                               headers={'Accept': 'application/json'}) as resp:
                if resp.status == 404:
                    embed = discord.Embed(title=f'Profile', colour=0xcc7474)
                    embed.add_field(name='Username not found',
                                    value=f'_{lichess_user}_ is not an active Lichess account.')
                    return await interaction.response.send_message(embed=embed)
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError:
                    return await interaction.response.send_message(f'Something went wrong with the Lichess API. '
                                                                   f'If this keeps happening, please report it on the '
                                                                   f'support server: https://discord.gg/KdpvMD72CV')
                lichess_response = await resp.json()

        try:
            embed = discord.Embed(title=f'{lichess_response["username"]}\'s profile',
                                  url=f'https://lichess.org/@/{lichess_user}',
                                  colour=0xdbd7ca)

            profile_contents = ''
            if 'profile' in lichess_response:
                profile = lichess_response['profile']
                if 'country' in profile:
                    embed.set_thumbnail(url=f'https://lichess1.org/assets/images/flags/{profile["country"]}.png')
                if 'location' in profile:
                    profile_contents += f'*Location:* {profile["location"]}\n'
                if 'bio' in profile:
                    profile_contents += f'*Bio:* {profile["bio"]}\n\n'
                if 'fideRating' in profile:
                    profile_contents += f'*FIDE rating:* {profile["fideRating"]}\n'

            profile_contents += f'*Play time:* {lichess_response["playTime"]["total"] // 60 // 60} hours\n'
            nr_games = lichess_response["count"]["all"]
            profile_contents += f'{nr_games} games played ' \
                                f'({lichess_response["count"]["win"] / nr_games * 100 :.1f}% win rate)'
            embed.add_field(name="Profile", value=profile_contents)

            if 'playing' in lichess_response:
                embed.add_field(name='Status', value=f'[Playing]({lichess_response["playing"]})')
            else:
                seen_datetime = datetime.fromtimestamp(lichess_response["seenAt"]//1000)
                if seen_datetime.date() == datetime.utcnow().date():
                    date_string = 'today'
                elif datetime.utcnow() - seen_datetime < timedelta(days=6):
                    date_string = 'on ' + calendar.day_name[seen_datetime.weekday()]
                else:
                    date_string = 'on ' + seen_datetime.date().isoformat()
                embed.add_field(name='Status', value=f'Last seen {date_string}')

            embed.add_field(name='Export games', value=f'[Download](https://lichess.org/api/games/user/{lichess_user})',
                            inline=False)
            await interaction.response.send_message(embed=embed)
        except KeyError as e:
            self.client.logger.critical(f'Error in profile command: Lichess API user object has no {e}')
            return await interaction.response.send_message(f'Something went wrong with the Lichess API. '
                                                           f'If this keeps happening, please report it on the '
                                                           f'support server: https://discord.gg/KdpvMD72CV')

        await self.client.update_user_rating(lichess_username=lichess_user)


async def setup(client: LichessBot):
    await client.add_cog(Profile(client),
                         guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Profile')

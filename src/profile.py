import lichess.api
import discord
from datetime import timedelta


async def show_profile(message, username):
    if username is None:  # TODO: no username = own profile
        username = 'stockvis'

    embed = discord.Embed(title=username,
                          colour=0x00ffff
                          )

    try:
        user = lichess.api.user(username)
        embed.url = f'https://lichess.org/@/{username}'
        embed.title = user['username']
    except lichess.api.ApiHttpError:
        embed.add_field(name='Error', value='This usename does not exist.')
        await message.channel.send(embed=embed)
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

    await message.channel.send(embed=embed)

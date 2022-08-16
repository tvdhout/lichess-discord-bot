import os

import topgg
from discord.ext import commands, tasks

from LichessBot import LichessBot


class TopGG(commands.Cog):
    """
    TopGG API Cog:
    https://top.gg/bot/707287095911120968
    """
    def __init__(self, client: LichessBot):
        self.client = client
        self.logger = self.client.logger
        self.token = os.getenv('TOPGG_TOKEN')
        self.topgg = topgg.DBLClient(self.client, self.token)
        self.update_stats.start()

    @tasks.loop(hours=2)
    async def update_stats(self):
        """
        Update server count every 4 hours
        @return:
        """
        self.logger.info('Attempting to post server count...')
        try:
            await self.topgg.post_guild_count()
            self.logger.info(f'Posted server count ({self.topgg.guild_count})')
        except Exception as e:
            self.logger.exception(f'Failed to post server count\n{type(e).__name__}: {e}')


async def setup(client: LichessBot):
    await client.add_cog(TopGG(client))
    client.logger.info("Sucessfully added cog: TopGG")

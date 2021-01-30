from discord.ext import commands, tasks
import dbl

from LichessBot import LichessBot


class TopGG(commands.Cog):
    """
    Post the bot's server count to Top.gg every hour.
    """
    def __init__(self, client: LichessBot):
        self.client = client
        self.logger = self.client.logger
        self.token = self.client.config.top_gg_token
        self.dblpy = dbl.DBLClient(self.client, self.token)
        self.update_stats.start()

    @tasks.loop(minutes=60.0)
    async def update_stats(self):
        """This function runs every 30 minutes to automatically update your server count"""
        self.logger.info('Attempting to post server count...')
        try:
            await self.dblpy.post_guild_count()
            self.logger.info(f'Posted server count ({self.dblpy.guild_count()})')
        except Exception as e:
            self.logger.exception(f'Failed to post server count\n{type(e).__name__}: {e}')


def setup(client: LichessBot):
    top_gg_cog = TopGG(client)
    client.add_cog(top_gg_cog)
    client.logger.info("Sucessfully added cog: TopGG")

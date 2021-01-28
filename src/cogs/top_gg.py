from discord.ext import commands
import dbl

from LichessBot import LichessBot


class TopGG(commands.Cog):
    """
    Post the bot's server count to Top.gg every 30 minutes.
    """
    def __init__(self, client: LichessBot):
        self.client = client
        self.token = self.client.config.top_gg_token
        self.dblpy = dbl.DBLClient(self.client, self.token, autopost=True)

    @commands.Cog.listener()
    async def on_guild_post(self):
        print("Server count posted successfully")


def setup(client: LichessBot):
    client.add_cog(TopGG(client))

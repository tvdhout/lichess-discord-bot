"""
Invite the bot to your server with the following URL
https://discord.com/api/oauth2/authorize?client_id=707287095911120968&permissions=52224&scope=bot
"""
import discord
from discord.ext import commands
import mysql.connector

from config import Config


class LichessBot(commands.Bot):
    def __init__(self, conf: Config, connection: mysql.connector.MySQLConnection, **kwargs):
        super().__init__(**kwargs)
        self.config = conf
        self.logger = conf.logger
        self.connection = connection

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user}")
        self.logger.info(f"Bot id: {self.user.id}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                             name=f"{self.config.prefix}help"))

    async def on_command_error(self, context, exception):
        if isinstance(exception, (commands.CommandNotFound, commands.NoPrivateMessage)):
            return
        self.logger.exception(f"{type(e).__name__}: {e}")
        raise exception


if __name__ == '__main__':
    RELEASE = True
    config = Config(release=RELEASE)

    try:
        config.logger.info("Connecting to database...")
        db_connection = mysql.connector.connect(user='thijs', host='localhost', database='lichess')

        try:
            config.logger.info("Initializing LichessBot...")
            client: LichessBot = LichessBot(conf=config, connection=db_connection, command_prefix=config.prefix)
            client.remove_command('help')  # remove default help command

            # Load command cogs
            config.logger.info("Loading extension cogs")
            extensions = ['cogs.profile', 'cogs.puzzle', 'cogs.rating', 'cogs.help']
            for extension in extensions:
                client.load_extension(extension)
            if RELEASE:
                client.load_extension('cogs.top_gg')
            config.logger.info("Finished loading extension cogs")

            client.run(config.token)
        except KeyboardInterrupt as e:
            config.logger.warning("Lichess bot stopped during setup. (KeyboardInterrupt)")
        finally:  # Gracefully close the connection
            db_connection.commit()
            db_connection.close()
            config.logger.info("Closed database connection\n\n")
    except mysql.connector.Error as e:
        config.logger.exception(f"MySQL connection error!\n{e}\n\n")

"""
Invite the bot to your server with the following URL
https://discord.com/api/oauth2/authorize?client_id=707287095911120968&permissions=52224&scope=bot
"""
import sys
from discord.ext import commands
import mysql.connector

from config import Config


class LichessBot(commands.Bot):
    def __init__(self, conf: Config, connection: mysql.connector.MySQLConnection, **kwargs):
        super().__init__(**kwargs)
        self.config = conf
        self.connection = connection

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        print("Bot id: ", self.user.id)

    async def on_command_error(self, context, exception):
        if isinstance(exception, (commands.CommandNotFound, commands.NoPrivateMessage)):
            return
        raise exception


if __name__ == '__main__':
    try:
        db_connection = mysql.connector.connect(user='thijs', host='localhost', database='lichess')

        try:
            config = Config(release=False)

            client: LichessBot = LichessBot(conf=config, connection=db_connection, command_prefix=config.prefix)
            client.remove_command('help')  # remove default help command

            # Load command cogs
            extensions = ['cogs.profile', 'cogs.puzzle', 'cogs.rating', 'cogs.help']
            for extension in extensions:
                client.load_extension(extension)

            client.run(config.token)
        except Exception as e:
            raise e
        finally:  # Gracefully close the connection
            db_connection.commit()
            db_connection.close()
    except mysql.connector.Error:
        print("Database connection error!", file=sys.stderr)

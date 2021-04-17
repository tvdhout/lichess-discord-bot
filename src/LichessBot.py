"""
Invite the bot to your server with the following URL
https://discord.com/api/oauth2/authorize?client_id=707287095911120968&permissions=116800&scope=bot
"""
from typing import Dict, List

import discord
from discord import Message
from discord.ext import commands
from discord.ext.commands import Context
import mysql.connector

from config import Config


class LichessBot(commands.Bot):
    def __init__(self, conf: Config, connection: mysql.connector.MySQLConnection, **kwargs):
        super().__init__(**kwargs)
        self.config = conf
        self.logger = conf.logger
        self.connection = connection
        self.prefixes: Dict[str, str] = self.retrieve_prefixes()  # {guild_id: prefix}

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user}")
        self.logger.info(f"Bot id: {self.user.id}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                             name=self.config.universal_prefix))

    async def on_command_error(self, context: Context, exception: Exception):
        if isinstance(exception, (commands.CommandNotFound, commands.NoPrivateMessage)):
            return
        self.logger.exception(f"{type(exception).__name__}: {exception}")
        raise exception

    async def on_guild_remove(self, guild):
        """
        Remove custom prefix, if set.
        @param guild: The guild from which the bot is removed.
        @return:
        """
        cursor = self.connection.cursor(buffered=True)
        cursor.execute("DELETE FROM prefixes WHERE guildId = %s", (str(guild.id),))
        cursor.close()
        self.connection.commit()

    def retrieve_prefixes(self) -> Dict[str, str]:
        """
        Retrieve all custom prefixes from the database.
        @return: dict: {guild_id: prefix}
        """
        cursor = self.connection.cursor(buffered=True)
        cursor.execute("SELECT guildId, prefix FROM prefixes")
        result = cursor.fetchall()
        cursor.close()
        self.connection.commit()
        return dict(result)

    def prefix(self, message: Message) -> List[str]:
        """
        Get the command prefix for the guild in which the message is sent.
        @param message: Message: message for which to request the prefix.
        @return: str: prefix
        """
        if message.guild is None:
            return [self.config.default_prefix, '']
        return [self.prefixes.get(str(message.guild.id), self.config.default_prefix)]

    def prfx(self, context: Context) -> str:
        return self.prefix(context.message)[-1]


def get_prefix(bot: LichessBot, message: Message) -> List[str]:
    return [bot.config.universal_prefix, *bot.prefix(message)]


if __name__ == '__main__':
    RELEASE = True
    config = Config(release=RELEASE)

    try:
        config.logger.info("Connecting to database...")
        db_connection = mysql.connector.connect(user='thijs', host='localhost', database='lichess')

        try:
            config.logger.info("Initializing LichessBot...")
            client: LichessBot = LichessBot(conf=config, connection=db_connection, command_prefix=get_prefix)
            client.remove_command('help')  # remove default help command

            # Load command cogs
            config.logger.info("Loading extension cogs")
            extensions = ['cogs.profile', 'cogs.puzzle', 'cogs.answer', 'cogs.rating', 'cogs.help']
            for extension in extensions:
                client.load_extension(extension)
            if RELEASE:
                client.load_extension('cogs.top_gg')
            config.logger.info("Finished loading extension cogs")

            client.run(config.token)
        except KeyboardInterrupt as e:
            config.logger.warning("Lichess bot stopped during setup. (KeyboardInterrupt)")
        finally:  # Gracefully close the database connection
            db_connection.commit()
            db_connection.close()
            config.logger.info("Closed database connection\n\n")
    except mysql.connector.Error as e:
        config.logger.exception(f"MySQL connection error!\n{e}\n\n")

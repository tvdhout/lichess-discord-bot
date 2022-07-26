"""
Invite the bot to your server with the following URL
https://discord.com/api/oauth2/authorize?client_id=707287095911120968&permissions=116800&scope=bot
"""
import os
import logging
from logging import handlers

import discord
from discord import Message
from discord.ext import commands
from discord.ext.commands import Context
from sqlalchemy.orm import sessionmaker

from database import engine


class LichessBot(commands.Bot):
    def __init__(self, release: bool = False, **kwargs):
        super().__init__(**kwargs, command_prefix=self.prefix)
        self.release = release
        self.logger = self._set_logger()
        self.base_dir: str = '/home/lichess/lichess-discord-bot'
        self.universal_prefix = "%lb"
        self.default_prefix = '-' if release else '$'
        self.Session = sessionmaker(bind=engine)
        self.prefixes: dict[str, str] = self.retrieve_prefixes()  # {guild_id: prefix}

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user}")
        self.logger.info(f"Bot id: {self.user.id}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                             name=self.universal_prefix))

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
        # TODO remove custom prefix from db
        ...

    def _set_logger(self) -> logging.getLoggerClass():
        logger = logging.getLogger('discord')
        logger.setLevel(logging.DEBUG)
        logging.getLogger('discord.http').setLevel(logging.INFO)

        file_handler = logging.handlers.RotatingFileHandler(
            filename='discord.log',
            encoding='utf-8',
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if not self.release:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
        return logger

    def retrieve_prefixes(self) -> dict[str, str]:
        """
        Retrieve all custom prefixes from the database.
        @return: dict: {guild_id: prefix}
        """
        result = ...  # TODO retrieve from db
        return dict(result)

    def prefix(self, message: Message) -> list[str]:
        """
        Get the command prefix for the guild in which the message is sent.
        @param message: Message: message for which to request the prefix.
        @return: str: prefix
        """
        if message.guild is None:  # Direct message
            return [self.default_prefix, '']
        return [self.universal_prefix, self.prefixes.get(str(message.guild.id), self.default_prefix)]

    def prfx(self, context: Context) -> str:
        return self.prefix(context.message)[-1]


if __name__ == '__main__':
    release = True

    client: LichessBot = LichessBot(release=release)
    client.remove_command('help')  # remove default help command

    # Load command cogs
    client.logger.info("Loading extension cogs")
    extensions = ['cogs.profile', 'cogs.puzzle', 'cogs.answer', 'cogs.rating', 'cogs.help']
    for extension in extensions:
        client.load_extension(extension)
    if release:
        client.load_extension('cogs.top_gg')
    client.logger.info("Finished loading extension cogs")

    client.run(token=os.getenv('DISCORD_TOKEN' if client.release else 'DISCORD_DEV_TOKEN'), log_handler=None)

"""
Invite the bot to your server with the following URL
TODO new link
"""
import os
import sys
import logging
from logging import handlers
from functools import cached_property

import discord
from aiohttp import ClientSession
from discord.ext import commands
from discord.ext.commands import Context
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from database import engine, Puzzle, ChannelPuzzle


class LichessBot(commands.Bot):
    def __init__(self, development: bool, **kwargs):
        super().__init__(**kwargs)
        self.__session: ClientSession | None = None
        self.synced = False
        self.development = development
        self.logger = self._set_logger()
        self.Session = sessionmaker(bind=engine)

    async def setup_hook(self):
        self.__session = ClientSession()
        # Load command cogs
        self.logger.info("Loading command cogs...")
        extensions = ['cogs.puzzle', 'cogs.answer', 'cogs.connect', 'cogs.rating', 'cogs.profile', 'cogs.about']
        for extension in extensions:
            await client.load_extension(extension)
        if not self.development:
            await client.load_extension('cogs.top_gg')
        self.logger.info("Finished loading extension cogs")

        if not self.synced:
            self.logger.info('Syncing commands')
            await client.tree.sync(guild=discord.Object(id=707286841577177140) if self.development else None)
            self.synced = True

    async def close(self):
        await super().close()
        await self.__session.close()

    async def on_ready(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                             name='Slash commands'))
        self.logger.info(f"Logged in as {self.user}")
        self.logger.info(f"Bot id: {self.user.id}")

    async def on_command_error(self, context: Context, exception: Exception):
        if isinstance(exception, (commands.CommandNotFound, commands.NoPrivateMessage)):
            return
        self.logger.exception(f"{type(exception).__name__}: {exception}")
        raise exception

    async def on_raw_thread_delete(self, payload: discord.RawThreadDeleteEvent):
        with self.Session() as session:
            session.query(ChannelPuzzle).filter(ChannelPuzzle.channel_id == payload.thread_id).delete()
            session.commit()

    @cached_property
    def total_nr_puzzles(self) -> int:
        with self.Session() as session:
            self.logger.info('Computing nr of puzzles...')
            return session.query(Puzzle).count()

    def _set_logger(self) -> logging.getLoggerClass():
        logger = logging.getLogger('discord')
        logger.setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.INFO)

        file_handler = logging.handlers.RotatingFileHandler(
            filename='discord.log',
            encoding='utf-8',
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('[{asctime}] [{levelname}] {name}: {message}', dt_fmt, style='{')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if self.development:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
        return logger


if __name__ == '__main__':
    load_dotenv()
    development = sys.argv[-1] == 'DEVELOPMENT'

    intents = discord.Intents.default()
    # intents.message_content = True
    client: LichessBot = LichessBot(development=development,
                                    command_prefix='%lb',
                                    application_id=os.getenv(f'{"DEV_" if development else ""}DISCORD_APPLICATION_ID'),
                                    intents=intents)
    client.run(token=os.getenv('DEV_DISCORD_TOKEN' if client.development else 'DISCORD_TOKEN'), log_handler=None)

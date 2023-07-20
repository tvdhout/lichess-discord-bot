"""
Invite the bot to your server with the following URL
https://discord.com/api/oauth2/authorize?client_id=707287095911120968&permissions=309237696512&scope=bot%20applications.commands
"""
import os
import sys
import logging
from logging import handlers

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Context
from async_property import async_cached_property
from aiohttp import ClientSession
from sqlalchemy import select, delete, func, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from database import async_engine, Puzzle, ChannelPuzzle, WatchedGame, User, Game
from logger import CustomFormatter


class LichessBot(commands.AutoShardedBot):
    def __init__(self, development: bool, **kwargs):
        super().__init__(**kwargs)
        self.__session: ClientSession | None = None
        self.synced = False
        self.development = development
        self.logger = self._set_logger(debug=development)
        self.Session = sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)

    async def setup_hook(self):
        self.logger.info(f"Running setup_hook for {'DEVELOPMENT' if self.development else 'PRODUCTION'}")
        self.__session = ClientSession()
        # Load command cogs
        self.logger.info("Loading command cogs...")
        extensions = ['cogs.puzzle', 'cogs.answer', 'cogs.connect', 'cogs.rating', 'cogs.profile', 'cogs.about',
                      'cogs.watch']
        for extension in extensions:
            await client.load_extension(extension)
        if not self.development:
            await client.load_extension('cogs.tasks')
        self.logger.info("Finished loading extension cogs")

        if not self.synced:
            self.logger.info('Syncing commands')
            await client.tree.sync(guild=discord.Object(id=707286841577177140) if self.development else None)
            self.synced = True

        # Delete WatchedGames from other session
        async with self.Session() as session:
            await session.execute(delete(WatchedGame))
        os.system('rm /tmp/*.png >/dev/null 2>&1')

    async def close(self):
        self.logger.debug('Called LichessBot.close')
        await super().close()
        await self.__session.close()

    async def on_ready(self):
        self.logger.debug('Called LichessBot.on_ready')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                             name='Slash commands'))
        self.logger.info(f"Logged in as {self.user}")
        self.logger.info(f"Bot id: {self.user.id}")

    async def on_command_error(self, context: Context, exception: Exception):
        self.logger.debug('Called LichessBot.on_command_error')
        if isinstance(exception, (commands.CommandNotFound, commands.NoPrivateMessage)):
            return
        self.logger.exception(f"{type(exception).__name__}: {exception}")
        raise exception

    async def on_raw_thread_delete(self, payload: discord.RawThreadDeleteEvent):
        self.logger.debug('Called LichessBot.on_raw_thread_delete')
        async with self.Session() as session:
            qs = [delete(ChannelPuzzle).where(ChannelPuzzle.channel_id == payload.thread_id),
                  delete(Game).where(Game.channel_id == payload.thread_id)]
            for q in qs:
                await session.execute(q)
            await session.commit()

    @async_cached_property
    async def total_nr_puzzles(self) -> int:
        self.logger.debug('Called LichessBot.total_nr_puzzles')
        async with self.Session() as session:
            return (await session.execute(select(func.count()).select_from(Puzzle))).first()[0]

    async def update_user_rating(self, lichess_username: str):
        self.logger.debug(f'Called LichessBot.update_user_rating({lichess_username})')
        async with aiohttp.ClientSession() as web:
            async with web.get(url=f'https://lichess.org/api/user/{lichess_username}',
                               headers={'Accept': 'application/json'}) as resp:
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError:
                    return
                lichess_response = await resp.json()

        async with self.Session() as session:
            try:
                await session.execute(update(User)
                                      .where(User.lichess_username == lichess_username)
                                      .values(puzzle_rating=lichess_response['perfs']['puzzle']['rating']))
                await session.commit()
            except KeyError:  # No puzzle rating
                pass

    @staticmethod
    def _set_logger(debug: bool) -> logging.getLoggerClass():
        logger = logging.getLogger('bot')
        logger.setLevel(logging.DEBUG if debug else logging.INFO)

        discord_logger = logging.getLogger('discord')
        discord_logger.setLevel(logging.INFO)

        formatter = CustomFormatter()

        file_handler = logging.handlers.RotatingFileHandler(
            filename='bot.log',
            encoding='utf-8',
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if debug:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
            discord_logger.addHandler(stream_handler)
        return logger


if __name__ == '__main__':
    load_dotenv()
    development = 'DEVELOPMENT' in sys.argv

    client: LichessBot = LichessBot(development=development,
                                    command_prefix='%lb',
                                    application_id=os.getenv(f'{"DEV_" if development else ""}DISCORD_APPLICATION_ID'),
                                    intents=discord.Intents.default())

    client.run(token=os.getenv('DEV_DISCORD_TOKEN' if client.development else 'DISCORD_TOKEN'), log_handler=None)

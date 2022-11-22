import asyncio
import os
import re
import json
import time
import aiohttp

import requests
import cairosvg
import chess
import discord
from chess import svg
from discord import app_commands
from discord.utils import MISSING
from discord.ext import commands
from sqlalchemy import select, delete

from LichessBot import LichessBot
from database import WatchedGame
from views import FlipBoardView


class Watch(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @staticmethod
    def format_seconds(sec: int) -> str:
        if sec >= 3600:
            return time.strftime('⏱ %Hh %Mm %Ss', time.gmtime(sec))
        if sec >= 60:
            return time.strftime('⏱ %Mm %Ss', time.gmtime(sec))
        return f'⏱ {sec}s'

    async def update_board(self, message: discord.Message, state: dict, white: str, black: str, flipped: bool):
        embed = message.embeds[0]
        embed.clear_fields()
        embed.colour = 0x000000 if flipped else 0xeeeeee
        embed.add_field(name=white, value=self.format_seconds(state['wc']), inline=True)
        embed.add_field(name=black, value=self.format_seconds(state['bc']), inline=True)

        board = chess.Board(state['fen'])
        lastmove_uci = state.get('lm', None)
        if lastmove_uci:
            lastmove = chess.Move(chess.parse_square(lastmove_uci[:2]),
                                  chess.parse_square(lastmove_uci[2:]))
        else:
            lastmove = None
        image = chess.svg.board(board,
                                lastmove=lastmove,
                                colors={'square light': '#f2d0a2', 'square dark': '#aa7249'},
                                flipped=flipped)
        cairosvg.svg2png(bytestring=str(image),
                         write_to=f'/tmp/{message.id}.png',
                         parent_width=1000,
                         parent_height=1000)
        file = discord.File(f'/tmp/{message.id}.png', filename=f"{message.id}.png")
        embed.set_image(url=f'attachment://{message.id}.png')
        await message.edit(embed=embed, attachments=[file])

    @app_commands.command(
        name='watch',
        description='Watch a (live) lichess game',
    )
    @app_commands.describe(url='the game ID, or a link to the game')
    async def watch(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        self.client.logger.debug('Called Watch.watch')
        msg = None
        match = re.match(r'https?://lichess\.org/([\w\d]{8})', url)
        if match is not None:
            game_id = match.group(1)
        else:
            game_id = url[:8]
        color: bool = chess.BLACK if 'black' in url else chess.WHITE
        try:
            async with aiohttp.ClientSession(raise_for_status=True) as req:
                async with req.get(url=f'https://lichess.org/game/export/{game_id}',
                                   headers={'Accept': 'application/json'}) as resp:
                    game = await resp.json()
        except (requests.HTTPError, json.JSONDecodeError):
            return await interaction.followup.send(f'There is no Lichess game with ID _{game_id}_. '
                                                   f'Note that game IDs are case sensitive.')
        if game['speed'] == 'correspondence':
            return await interaction.followup.send(f"I'm sorry, I can't follow correspondence games.")

        variant = ' '.join(re.findall(r'[a-z]+|([A-Z\d][a-z]*)', game['variant'])).lower()
        white_player, black_player = game['players']['white'], game['players']['black']

        try:
            title = f'_{t}_ ' if (t := white_player["user"].get("title", "")) != '' else ''
            white_player_str = f'⚪️️ {title}' \
                               f'{white_player["user"]["name"]} ' \
                               f'({white_player["rating"]}' \
                               f'{"?" if white_player.get("provisional", False) else ""})'
        except KeyError:
            white_player_str = f'⚪️️ Stockfish level {white_player["aiLevel"]}'
            color = chess.BLACK
        try:
            title = f'_{t}_ ' if (t := black_player["user"].get("title", "")) != '' else ''
            black_player_str = f'⚫️️ {title}' \
                               f'{black_player["user"]["name"]} ' \
                               f'({black_player["rating"]}' \
                               f'{"?" if black_player.get("provisional", False) else ""})'
        except KeyError:
            black_player_str = f'⚫️️ Stockfish level {black_player["aiLevel"]}'
            color = chess.WHITE
        initial_sec = game["clock"]["initial"]

        embed_title = (
            f'{"Rated" if game["rated"] else "Casual"}'
            f'{(variant + " ") if variant != "Standard" else ""}'
            f'{game["speed"].capitalize()} '
            f'game '
            f'({initial_sec // 60}{f":{initial_sec % 60}" if initial_sec % 60 != 0 else ""}'
            f'+{game["clock"]["increment"]})'
        )
        embed = discord.Embed(url=f'https://lichess.org/{game_id}',
                              color=0xeeeeee if color == chess.WHITE else 0x000000)

        if game['status'] in ['created', 'started']:  # Game is ongoing
            await interaction.followup.send(f'Watching game `{game_id}`\n'
                                            f'_Note: live game streams are 3 moves behind the actual game._')
            embed.title = 'LIVE: ' + embed_title
            embed.add_field(name=white_player_str, value='⏱ _Please wait..._', inline=True)
            embed.add_field(name=black_player_str, value='⏱ _Please wait..._', inline=True)

            async with aiohttp.ClientSession() as web:
                try:
                    async with web.get(f'https://lichess.org/api/stream/game/{game_id}', timeout=3600) as stream:
                        game_state = json.loads(await stream.content.readline())
                        board = chess.Board(game_state['fen'])
                        latest_fen = ' '.join(game_state['fen'].split()[:2])
                        lastmove_uci = game_state.get('lastMove', None)
                        if lastmove_uci is not None:
                            lastmove = chess.Move(chess.parse_square(lastmove_uci[:2]),
                                                  chess.parse_square(lastmove_uci[2:]))
                        else:
                            lastmove = None
                        image = chess.svg.board(board, lastmove=lastmove,
                                                colors={'square light': '#f2d0a2', 'square dark': '#aa7249'},
                                                flipped=(color == chess.BLACK))
                        cairosvg.svg2png(bytestring=str(image),
                                         write_to=f'/tmp/{game_id}.png',
                                         parent_width=1000,
                                         parent_height=1000)
                        file = discord.File(f'/tmp/{game_id}.png', filename=f"{game_id}.png")
                        embed.set_image(url=f'attachment://{game_id}.png')
                        msg = await interaction.channel.send(embed=embed, file=file,
                                                             view=FlipBoardView(sessionmaker=self.client.Session))
                        async with self.client.Session() as session:
                            session.add(
                                WatchedGame(message_id=msg.id,
                                            watcher_id=interaction.user.id,
                                            game_id=game_id,
                                            color=color))
                            await session.commit()

                        up_to_date = False

                        async with self.client.Session() as session:
                            stop = False
                            async for line in stream.content:
                                if line == b'\n':  # Sent to keep open the connection
                                    continue
                                state = json.loads(line)
                                assert 'wc' in state, "Game over, summary shown"
                                if not up_to_date:
                                    if state['fen'] == latest_fen:
                                        up_to_date = True
                                    else:
                                        continue
                                color: bool = (await (session.execute(
                                    select(WatchedGame.color)
                                    .filter(WatchedGame.message_id == msg.id))
                                )).scalar()
                                try:
                                    await self.update_board(message=msg, state=state, white=white_player_str,
                                                            black=black_player_str, flipped=color == chess.BLACK)
                                except discord.errors.NotFound:
                                    stop = True
                                    break
                            raise InterruptedError  # Game finished
                except (asyncio.exceptions.TimeoutError, InterruptedError, AssertionError):
                    async with self.client.Session() as session:
                        await session.execute(delete(WatchedGame)
                                              .where(WatchedGame.message_id == msg.id))
                        await session.commit()
                    if os.path.exists(f'/tmp/{game_id}.png'):
                        os.remove(f'/tmp/{game_id}.png')
                    if stop:  # Message with game deleted
                        return

        else:  # Game is not ongoing at command invocation
            await interaction.followup.send(f'Replaying game `{game_id}`:')

        embed = discord.Embed(title=embed_title, url=f'https://lichess.org/{game_id}',
                              color=0xeeeeee if color else 0x000000)
        embed.set_image(url=f'https://lichess1.org/game/export/gif/{"white" if color else "black"}/'
                            f'{game_id}.gif')

        if msg is not None:  # Game was previously in progres, get the updated stats
            game = requests.get(url=f'https://lichess.org/game/export/{game_id}',
                                headers={'Accept': 'application/json'}).json()

        def analysis(color) -> str:
            p: dict = game['players'][color]
            a = '{0:+d} rating points'.format(p['ratingDiff']) if p.get('ratingDiff', None) is not None else 'N/A'
            try:
                _a = p["analysis"]
                a += f'\n\n**Analysis**:\n'
                a += f'Inaccuraies: {_a["inaccuracy"]}\n'
                a += f'Mistakes: {_a["mistake"]}\n'
                a += f'Blunders: {_a["blunder"]}\n'
                a += f'Centipawn loss: {_a["acpl"]}'
            except KeyError:
                pass
            return a

        embed.add_field(name=white_player_str, value=analysis('white'), inline=True)
        embed.add_field(name=black_player_str, value=analysis('black'), inline=True)
        if msg is None:
            await interaction.channel.send(embed=embed, view=FlipBoardView(sessionmaker=self.client.Session))
        else:
            await msg.edit(embed=embed, view=FlipBoardView(sessionmaker=self.client.Session), attachments=[])


async def setup(client: LichessBot):
    await client.add_cog(Watch(client), guild=discord.Object(id=707286841577177140) if client.development else MISSING)
    client.logger.info('Sucessfully added cog: Watch')

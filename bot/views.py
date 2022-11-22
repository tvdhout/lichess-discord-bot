import os
import re

import discord
from discord.ui import View, Button
from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker, selectinload
import chess
from chess import svg
from cairosvg import svg2png

from database import ChannelPuzzle, WatchedGame


class ConnectView(View):
    def __init__(self, url: str):
        super().__init__()
        connect_button = Button(label='Click here to connect your Lichess account', emoji='🔗', url=url)
        self.add_item(connect_button)


class FlipBoardView(View):
    def __init__(self, sessionmaker: sessionmaker):
        super().__init__(timeout=7200.0)
        self.Session = sessionmaker

    @discord.ui.button(label='Flip board', emoji='🔃', style=discord.ButtonStyle.gray)
    async def flip_board(self, interaction: discord.Interaction, button: Button):
        async with self.Session() as session:
            game: WatchedGame = (await session.execute(select(WatchedGame)
                                                       .filter(WatchedGame.message_id == interaction.message.id)
                                                       )).scalar()
            embed = interaction.message.embeds[0]
            # Gif of past game
            if game is None:
                new_color = 'white' not in embed.image.url
                embed.set_image(url=embed.image.url.replace('white', '???').replace('black', 'white')
                                .replace('???', 'black'))
                embed.colour = 0xeeeeee if new_color else 0x000000
                return await interaction.response.edit_message(embed=embed)

            # Live game
            if not game.watcher_id == interaction.user.id:
                return await interaction.response.send_message('Only the person who requested the game may flip '
                                                               'the board.', ephemeral=True, delete_after=5)
            game.color = not game.color
            await interaction.response.send_message('The board will flip at the next move.', ephemeral=True,
                                                        delete_after=3)
            await session.execute(update(WatchedGame)
                                  .where(WatchedGame.message_id == interaction.message.id)
                                  .values(color=game.color))
            await session.commit()


class UpdateBoardView(View):
    def __init__(self, sessionmaker: sessionmaker):
        super().__init__(timeout=3600.0)
        self.Session = sessionmaker

    @discord.ui.button(label='Show updated board', emoji='🧩', style=discord.ButtonStyle.blurple)
    async def show_updated_board(self, interaction: discord.Interaction, button: Button):
        async with self.Session() as session:
            c_puzzle = (await session.execute(select(ChannelPuzzle)
                                              .filter(ChannelPuzzle.channel_id == interaction.channel_id)
                                              .options(selectinload(ChannelPuzzle.puzzle)))).scalar()
            if c_puzzle is None:
                button.disabled = True
                await interaction.response.edit_message(view=self)
                return await interaction.followup.send('There is no active puzzle in this channel! Start a '
                                                       'puzzle with any of the `/puzzle` commands',
                                                       ephemeral=True)

            # Play the puzzle's moves to the current state of the channel puzzle.
            board = chess.Board(c_puzzle.puzzle.fen)
            played_moves_uci = c_puzzle.puzzle.moves[:-len(c_puzzle.moves)]
            move = None
            for m in played_moves_uci:
                move = board.parse_uci(m)
                board.push(move)

            color = 'black' if ' w ' in c_puzzle.puzzle.fen else 'white'

            image = svg.board(board, lastmove=move, colors={'square light': '#f2d0a2', 'square dark': '#aa7249'},
                              flipped=(color == 'black'))

            svg2png(bytestring=str(image), write_to=f'/tmp/{interaction.channel_id}.png', parent_width=1000,
                    parent_height=1000)
            embed = discord.Embed(title=f"Updated board ({color} to play)",
                                  colour=0xeeeeee if color == 'white' else 0x000000)
            puzzle = discord.File(f'/tmp/{interaction.channel_id}.png',
                                  filename="board.png")  # load puzzle as Discord file
            embed.set_image(url="attachment://board.png")

            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(file=puzzle, embed=embed, view=HintView(sessionmaker=self.Session))

            # Delete board image
            if os.path.exists(f'/tmp/{interaction.channel_id}.png'):
                os.remove(f'/tmp/{interaction.channel_id}.png')


class HintView(View):
    pieces = {'R': 'rook', 'N': 'knight', 'B': 'bishop', 'Q': 'queen', 'K': 'king'}

    def __init__(self, sessionmaker: sessionmaker):
        super().__init__(timeout=3600.0)
        self.Session = sessionmaker

    @discord.ui.button(label='Get a hint', emoji='❓', style=discord.ButtonStyle.gray)
    async def hint(self, interaction: discord.Interaction, button: Button):
        async with self.Session() as session:
            c_puzzle = (await session.execute(select(ChannelPuzzle)
                                              .filter(ChannelPuzzle.channel_id == interaction.channel_id)
                                              .options(selectinload(ChannelPuzzle.puzzle)))).scalar()
            if c_puzzle is None:
                button.disabled = True
                await interaction.response.edit_message(view=self)
                try:
                    return await interaction.response.send_message('There is no active puzzle in this channel! Start a '
                                                                   'puzzle with any of the `/puzzle` commands',
                                                                   ephemeral=True)
                except discord.errors.InteractionResponded:
                    return await interaction.followup.send('There is no active puzzle in this channel! Start a '
                                                           'puzzle with any of the `/puzzle` commands',
                                                           ephemeral=True)
            board = chess.Board(c_puzzle.fen)
            next_uci = c_puzzle.moves[0]
            move = board.san(board.parse_uci(next_uci))
            piece = self.pieces.get(move[0], "pawn")
            themes: list[str] = []
            for theme in c_puzzle.puzzle.themes:
                themes.append(' '.join(re.findall(r'[a-z]+|(?:[A-Z\d][a-z]*)', theme)).capitalize())
            await interaction.response.send_message(f'(Click to reveal)\nThe themes of this puzzle are: '
                                                    f'||{", ".join(themes)}||\nYou should move your ||{piece}||',
                                                    ephemeral=True)


class WrongAnswerView(HintView):
    def __init__(self, sessionmaker: sessionmaker):
        super().__init__(sessionmaker=sessionmaker)
        self.Session = sessionmaker

    @discord.ui.button(label='I give up', emoji='🤯', style=discord.ButtonStyle.red)
    async def best_move(self, interaction: discord.Interaction, button: Button):
        button.disabled = True
        async with self.Session() as session:
            c_puzzle = (await session.execute(select(ChannelPuzzle)
                                              .filter(ChannelPuzzle.channel_id == interaction.channel_id)
                                              .options(selectinload(ChannelPuzzle.puzzle)))).scalar()
            await interaction.response.edit_message(view=self)
            if c_puzzle is None:
                return await interaction.followup.send('There is no active puzzle in this channel! Start a puzzle with '
                                                       'any of the `/puzzle` commands', ephemeral=True)

            embed = discord.Embed(title=f'The best move is...', color=0x74a7cc)

            moves = c_puzzle.moves
            board = chess.Board(c_puzzle.fen)
            correct_uci = moves.pop(0)
            correct_san = board.san(board.parse_uci(correct_uci))
            if len(moves) == 0:  # Last move
                embed.add_field(name=correct_san,
                                value=f'The best move is {correct_san} (or {correct_uci}). You completed the puzzle! '
                                      f'(difficulty rating {c_puzzle.puzzle.rating})')
                await interaction.followup.send(embed=embed)
                await session.delete(c_puzzle)
            else:
                board.push_uci(correct_uci)
                reply_uci = moves.pop(0)
                move = board.parse_uci(reply_uci)
                reply_san = board.san(move)
                board.push(move)

                embed.add_field(name=correct_san,
                                value=f'The best move is {correct_san} (or {correct_uci}). The opponent responded with '
                                      f'{reply_san}. Now what\'s the best move?')

                await interaction.followup.send(embed=embed, view=UpdateBoardView(sessionmaker=self.Session))

                await session.execute(update(ChannelPuzzle)
                                      .where(ChannelPuzzle.channel_id == c_puzzle.channel_id)
                                      .values(moves=moves, fen=board.fen()))
            await session.commit()

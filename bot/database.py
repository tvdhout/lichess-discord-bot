import os
import sys
from typing import Optional
from typing_extensions import Annotated
from datetime import datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy import ARRAY, SmallInteger, BigInteger, String, create_engine
from sqlalchemy.orm import Session, Mapped, mapped_column, relationship, DeclarativeBase, MappedAsDataclass
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.dialects import postgresql
from psycopg2.extensions import AsIs

load_dotenv()
async_engine = create_async_engine(f'postgresql+asyncpg://{os.getenv("DATABASE_USER")}'
                                   f':{os.getenv("DATABASE_PASSWORD")}'
                                   f'@{os.getenv("DATABASE_HOST")}'
                                   f'/{os.getenv("DATABASE_NAME")}')
sync_engine = create_engine(f'postgresql://{os.getenv("DATABASE_USER")}'
                            f':{os.getenv("DATABASE_PASSWORD")}'
                            f'@{os.getenv("DATABASE_HOST")}'
                            f'/{os.getenv("DATABASE_NAME")}')

# Type annotations
fenstring = Annotated[str, String(90)]
chessmoves = Annotated[list, mapped_column(ARRAY(String(5)))]
bigintpk = Annotated[int, mapped_column(BigInteger, primary_key=True)]
smallint = Annotated[int, mapped_column(SmallInteger)]


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class Game(Base):
    """
    Table for chess games currently in play on Discord
    """
    __tablename__ = 'games'

    channel_id: Mapped[bigintpk]
    white_player_id: Mapped[int] = mapped_column(BigInteger)
    black_player_id: Mapped[int] = mapped_column(BigInteger)
    fen: Mapped[str] = mapped_column(String(length=90))
    last_move: Mapped[Optional[str]] = mapped_column(String(length=4))
    time_last_move: Mapped[Optional[datetime]]
    whites_turn: Mapped[bool] = mapped_column(default=True)


class Puzzle(Base):
    """
    Table containing chess puzzles
    https://database.lichess.org/#puzzles
    """
    __tablename__ = 'puzzles'

    puzzle_id: Mapped[str] = mapped_column(primary_key=True)
    fen: Mapped[fenstring]
    moves: Mapped[chessmoves]
    rating: Mapped[smallint] = mapped_column(index=True)
    rating_deviation: Mapped[smallint]
    popularity: Mapped[smallint]
    nr_plays: Mapped[int]
    url: Mapped[str]
    opening_tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))

    channels: Mapped[list['ChannelPuzzle']] = relationship(cascade='all, delete, delete-orphan, save-update',
                                                           back_populates='puzzle')
    themes: Mapped[list[str]] = mapped_column(ARRAY(String), default_factory=list)

    # GIN index on themes
    __table_args__ = (sa.Index('ix_puzzles_themes', themes, postgresql_using='gin'),)


class ChannelPuzzle(Base):
    """
    Table containing puzzles that are currently being solved in a channel
    """
    __tablename__ = 'channel_puzzles'

    channel_id: Mapped[bigintpk]  # channel_id of the active channel
    puzzle_id: Mapped[str] = mapped_column(sa.ForeignKey('puzzles.puzzle_id'), index=True)
    puzzle: Mapped['Puzzle'] = relationship(back_populates='channels', init=False)
    moves: Mapped[chessmoves]
    fen: Mapped[fenstring]  # FEN updated according to the progress


class APIChallenge(Base):
    """
    Lichess API PKCE challenge state
    """
    __tablename__ = 'api_challenges'

    discord_id: Mapped[bigintpk]
    code_verifier: Mapped[str] = mapped_column(String(64))


class User(Base):
    """
    Discord user and connected Lichess account
    """
    __tablename__ = 'users'

    discord_id: Mapped[bigintpk]
    lichess_username: Mapped[str] = mapped_column(String(20))
    puzzle_rating: Mapped[Optional[smallint]]


class WatchedGame(Base):
    __tablename__ = 'watched_games'

    message_id: Mapped[bigintpk]
    watcher_id: Mapped[int] = mapped_column(BigInteger)  # Discord ID of person who invoked the watch command
    game_id: Mapped[str] = mapped_column(String(8))
    color: Mapped[bool]  # white = True


def drop_database():
    insp = sa.inspect(sync_engine)
    with sync_engine.begin() as conn:
        for table_entry in reversed(insp.get_sorted_table_and_fkc_names()):
            table_name = table_entry[0]
            if table_name:
                conn.execute(sa.text('DROP TABLE :t CASCADE'), {'t': AsIs(table_name)})


def update_puzzles_table():
    """
    1. Downloads the puzzle database from https://database.lichess.org/lichess_db_puzzle.csv.bz2
    2. Unzip the csv
    3. In manageble chunks, read the CSV with pandas, transform the columns where needed, and ingest puzzles in the
    database, updating puzzles where present
    """
    try:
        os.system('wget -O /tmp/puzzles.csv.zst https://database.lichess.org/lichess_db_puzzle.csv.zst '
                  '&& unzstd -f --rm /tmp/puzzles.csv.zst')
        with Session(bind=sync_engine) as session:
            with pd.read_csv('/tmp/puzzles.csv', chunksize=1000,
                             names=['puzzle_id', 'fen', 'moves', 'rating', 'rating_deviation', 'popularity', 'nr_plays',
                                    'themes', 'url', 'opening_tags'], header=0) as reader:
                for df in reader:
                    with session.begin():
                        df['moves'] = df['moves'].map(str.split)
                        df['themes'] = df['themes'].map(str.split, na_action='ignore')
                        df['opening_tags'] = df['opening_tags'].map(str.split, na_action='ignore')
                        df['opening_tags'] = df['opening_tags'].map(lambda lst: [tag.replace('_', ' ') for tag in lst],
                                                                    na_action='ignore')
                        df.replace({np.nan: None}, inplace=True)
                        insert_statement = postgresql.insert(Puzzle.__table__).values(df.to_dict(orient='records'))
                        upsert_statement = insert_statement.on_conflict_do_update(index_elements=['puzzle_id'],
                                                                                  set_={c.key: c for c in
                                                                                        insert_statement.excluded if
                                                                                        c.key != 'puzzle_id'})
                        session.execute(upsert_statement)
    finally:
        if os.path.exists('/tmp/puzzles.csv'):
            os.remove('/tmp/puzzles.csv')


if __name__ == '__main__':
    if 'RESET' in sys.argv:
        answer = input('Drop tables? y/n ')
        if answer.lower() == 'y':
            drop_database()
        else:
            print("Not dropping tables.")
    Base.metadata.create_all(bind=sync_engine)
    if 'UPDATE' in sys.argv:
        update_puzzles_table()

import os
import sys
import numpy as np
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, Column, ARRAY, Integer, SmallInteger, String, text, inspect, ForeignKey
from sqlalchemy.orm import Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql
from psycopg2.extensions import AsIs

load_dotenv(find_dotenv('.env'))
Base = declarative_base()
engine = create_engine(f'postgresql://{os.getenv("DATABASE_USER")}'
                       f':{os.getenv("DATABASE_PASSWORD")}'
                       f'@{os.getenv("DATABASE_HOST")}'
                       f'/{os.getenv("DATABASE_NAME")}')
# TODO maybe this is obsolete:
PUZZLE_DTYPES = {'puzzle_id': String, 'fen': String(length=90), 'moves': ARRAY(String), 'rating': SmallInteger,
                 'rating_deviation': SmallInteger, 'popularity': SmallInteger, 'nr_plays': Integer,
                 'themes': ARRAY(String), 'url': String, 'opening_family': String, 'opening_variation': String}


class Puzzle(Base):
    """
    Table containing chess puzzles
    https://database.lichess.org/#puzzles
    """
    __tablename__ = 'puzzles'

    # id: Column = Column(BigInteger, nullable=False, autoincrement=True, index=True)
    puzzle_id: Column = Column(String, primary_key=True, nullable=False, unique=True, index=True)
    fen: Column = Column(String(length=90), nullable=False)
    moves: Column = Column(ARRAY(String), nullable=False)
    rating: Column = Column(SmallInteger, nullable=False, index=True)
    rating_deviation: Column = Column(SmallInteger, nullable=False)
    popularity: Column = Column(SmallInteger, nullable=False)
    nr_plays: Column = Column(Integer, nullable=False)
    themes: Column = Column(ARRAY(String))
    url: Column = Column(String, nullable=False)
    opening_family: Column = Column(String)
    opening_variation: Column = Column(String)

    channels = relationship('ChannelPuzzle', cascade='all, delete, delete-orphan, save-update', backref='puzzle')


class Prefix(Base):
    """
    Tabling containing the custom command prefix for each guild that changed the default
    """
    __tablename__ = 'prefixes'

    guild_id: Column = Column(String, primary_key=True, nullable=False)  # Guild ID of the updated prefix
    prefix: Column = Column(String(10), nullable=False)  # Command prefix character(s) (default '-')


class ChannelPuzzle(Base):
    """
    Table containing puzzles that are currently being solved in a channel
    """
    __tablename__ = 'channel_puzzles'

    channel_id: Column = Column(String, primary_key=True, nullable=False)  # channel_id in which the puzzle in played
    puzzle_id: Column = Column(String, ForeignKey('puzzles.puzzle_id'), nullable=False)
    # puzzle: Puzzle object backreferenced from relationship
    moves: Column = Column(ARRAY(String), nullable=False)  # List of moves left in the puzzle
    fen: Column = Column(String, nullable=False)  # FEN updated according to the progress
    message_id: Column = Column(String, nullable=False)  # Message ID referencing the message that triggered the command


class User(Base):
    """
    Discord user and connected Lichess account
    """
    __tablename__ = 'users'

    discord_uid: Column = Column(String, primary_key=True, nullable=False, index=True)
    lichess_username: Column = Column(String(20), nullable=False)
    puzzle_rating: Column = Column(SmallInteger, nullable=False)


def drop_database():
    insp = inspect(engine)
    for table_entry in reversed(insp.get_sorted_table_and_fkc_names()):
        table_name = table_entry[0]
        if table_name:
            with engine.begin() as conn:
                conn.execute(text('DROP TABLE :t CASCADE'), {'t': AsIs(table_name)})


def update_puzzles_table():
    """
    1. Downloads the puzzle database from https://database.lichess.org/lichess_db_puzzle.csv.bz2
    2. Unzip the csv
    3. In manageble chunks, read the CSV with pandas, transform the columns where needed, and ingest puzzles in the
    database, updating puzzles where present
    """
    session = Session(bind=engine)
    os.system('wget -O /tmp/puzzles.csv.bz2 https://database.lichess.org/lichess_db_puzzle.csv.bz2'
              '&& bunzip2 /tmp/puzzles.csv.bz2')

    try:
        with pd.read_csv('/tmp/puzzles.csv', chunksize=10_000,
                         names=list(PUZZLE_DTYPES.keys())) as reader:
            for df in reader:
                print('10k')
                df.moves = df.moves.map(str.split)
                df.themes = df.themes.map(str.split, na_action='ignore')
                df.opening_family = df.opening_family.str.replace('_', ' ', regex=False)
                df.opening_variation = df.opening_variation.str.replace('_', ' ', regex=False)
                df.replace({np.nan: None}, inplace=True)

                insert_statement = postgresql.insert(Puzzle.__table__).values(df.to_dict(orient='records'))
                upsert_statement = insert_statement.on_conflict_do_update(index_elements=['puzzle_id'],
                                                                          set_={c.key: c for c in
                                                                                insert_statement.excluded if
                                                                                c.key != 'puzzle_id'})
                session.execute(upsert_statement)
                session.commit()
    finally:
        os.remove('/tmp/puzzles.csv')


if __name__ == '__main__':
    if 'RESET' in sys.argv:
        answer = input('Drop tables? y/n ')
        if answer.lower() == 'y':
            drop_database()
        else:
            print("Not dropping tables.")
    Base.metadata.create_all(engine)
    if 'UPDATE' in sys.argv:
        update_puzzles_table()

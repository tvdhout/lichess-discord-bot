import os
import sys
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy import Column, ARRAY, Integer, SmallInteger, BigInteger, String, Text
from sqlalchemy.orm import Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql
from psycopg2.extensions import AsIs

load_dotenv()
Base = declarative_base()
engine = sa.create_engine(f'postgresql://{os.getenv("DATABASE_USER")}'
                          f':{os.getenv("DATABASE_PASSWORD")}'
                          f'@{os.getenv("DATABASE_HOST")}'
                          f'/{os.getenv("DATABASE_NAME")}')


class Puzzle(Base):
    """
    Table containing chess puzzles
    https://database.lichess.org/#puzzles
    """
    __tablename__ = 'puzzles'

    puzzle_id: Column | str = Column(String, primary_key=True, nullable=False, unique=True)
    fen: Column | str = Column(String(length=90), nullable=False)
    moves: Column | list[str] = Column(ARRAY(String(4)), nullable=False)
    rating: Column | int = Column(SmallInteger, nullable=False, index=True)
    rating_deviation: Column | int = Column(SmallInteger, nullable=False)
    popularity: Column | int = Column(SmallInteger, nullable=False)
    nr_plays: Column | int = Column(Integer, nullable=False)
    themes: Column | list[str] = Column(postgresql.ARRAY(Text), nullable=False, default=[])
    url: Column | str = Column(String, nullable=False)
    opening_family: Column | str = Column(String)
    opening_variation: Column | str = Column(String)

    channels = relationship('ChannelPuzzle', cascade='all, delete, delete-orphan, save-update', backref='puzzle')

    # GIN index on themes
    __table_args__ = (sa.Index('ix_puzzles_themes', themes, postgresql_using="gin"),)


class ChannelPuzzle(Base):
    """
    Table containing puzzles that are currently being solved in a channel
    """
    __tablename__ = 'channel_puzzles'

    channel_id: Column | int = Column(BigInteger, primary_key=True, nullable=False)  # channel_id of the active channel
    puzzle_id: Column | str = Column(String, sa.ForeignKey('puzzles.puzzle_id'), nullable=False, index=True)
    # puzzle: Puzzle object backreferenced from relationship
    moves: Column | list[str] = Column(ARRAY(String(4)), nullable=False)  # List of moves left in the puzzle
    fen: Column | str = Column(String, nullable=False)  # FEN updated according to the progress


class APIChallenge(Base):
    """
    Lichess API PKCE challenge state
    """
    __tablename__ = 'api_challenges'

    discord_id: Column | int = Column(BigInteger, primary_key=True, nullable=False)
    code_verifier: Column | str = Column(String(64), nullable=False)


class User(Base):
    """
    Discord user and connected Lichess account
    """
    __tablename__ = 'users'

    discord_id: Column | int = Column(BigInteger, primary_key=True, nullable=False)
    lichess_username: Column | str = Column(String(20), nullable=False)
    puzzle_rating: Column | int = Column(SmallInteger, nullable=False)


def drop_database():
    insp = sa.inspect(engine)
    for table_entry in reversed(insp.get_sorted_table_and_fkc_names()):
        table_name = table_entry[0]
        if table_name:
            with engine.begin() as conn:
                conn.execute(sa.text('DROP TABLE :t CASCADE'), {'t': AsIs(table_name)})


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
                         names=['puzzle_id', 'fen', 'moves', 'rating', 'rating_deviation', 'popularity', 'nr_plays',
                                'themes', 'url', 'opening_family', 'opening_variation']) as reader:
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
        if os.path.exists('/tmp/puzzles.csv'):
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

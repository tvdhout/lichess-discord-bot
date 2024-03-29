import os
import sys

import flask
import requests
from dotenv import load_dotenv
from flask import Flask, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
sys.path.append(os.getenv('BASE_DIR'))

from bot.database import APIChallenge, User


app = Flask(__name__)
app.config['SERVER_NAME'] = 'lichess.' + os.getenv('FQDN')

engine = create_engine(f'postgresql://{os.getenv("DATABASE_USER")}'
                       f':{os.getenv("DATABASE_PASSWORD")}'
                       f'@{os.getenv("DATABASE_HOST")}'
                       f'/{os.getenv("DATABASE_NAME")}')
Session = sessionmaker(bind=engine)


@app.route('/test')
def test_page():
    return flask.render_template('test.html')


@app.route('/callback')
def callback():
    error = request.args.get('error', type=str)
    code = request.args.get('code', type=str)
    try:
        state = request.args.get('state', type=int)
    except ValueError:
        return flask.render_template('error.html')

    if error is not None or code is None or state is None:
        return flask.render_template('error.html')

    with Session() as session:
        challenge_query = session.query(APIChallenge).filter(APIChallenge.discord_id == state)
        challenge: APIChallenge | None = challenge_query.first()
        if challenge is None:
            return flask.render_template('expired.html')

        # Get OAuth token
        resp = requests.post(url='https://lichess.org/api/token',
                             json={
                                 'grant_type': 'authorization_code',
                                 'code': code,
                                 'code_verifier': challenge.code_verifier,
                                 'redirect_uri': os.getenv('CONNECT_REDIRECT_URI'),
                                 'client_id': os.getenv('CONNECT_CLIENT_ID')
                             })
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            return flask.render_template('error.html')
        content = resp.json()

        # Check connected user data
        resp = requests.get(url='https://lichess.org/api/account',
                            headers={'Authorization': f'Bearer {content["access_token"]}'})
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            return flask.render_template('error.html')
        content = resp.json()
        username = content['id']
        try:
            puzzle_rating = content['perfs']['puzzle']['rating']
        except KeyError:
            puzzle_rating = None

        session.merge(User(discord_id=state, lichess_username=username, puzzle_rating=puzzle_rating))
        challenge_query.delete()
        session.commit()

    return flask.render_template('success.html', username=username)


# uWSGI application
application = app

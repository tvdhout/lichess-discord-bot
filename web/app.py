import os
import sys

import flask
import requests
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
sys.path.append(os.getenv('BASE_DIR'))

from bot.database import APIChallenge, User

app = Flask(__name__)
app.config['SERVER_NAME'] = os.getenv('FQDN')

engine = create_engine(f'postgresql://{os.getenv("DATABASE_USER")}'
                       f':{os.getenv("DATABASE_PASSWORD")}'
                       f'@{os.getenv("DATABASE_HOST")}'
                       f'/{os.getenv("DATABASE_NAME")}')
Session = sessionmaker(bind=engine)


@app.route('/test')
# @app.route('/')
def test_page():
    return flask.render_template('test.html')


@app.route('/success')
def success():
    username = flask.session.get('username', None)
    if username is None:
        return flask.render_template('exceptions.html', code=400, description="You shouldn't be here 👀"), 400
    return flask.render_template('success.html', username=username)


@app.route('/error')
def error():
    return flask.render_template('error.html')


@app.route('/expired')
def expired():
    return flask.render_template('expired.html')


@app.route('/callback')
async def callback():
    try:
        error = request.args.get('error', type=str)
        code = request.args.get('code', type=str)
        state = request.args.get('state', type=int)  # TODO insert some randomness in state, next to discord ID
    except ValueError:
        return redirect(url_for('error'))

    if error is not None or code is None or state is None:
        return redirect(url_for('error'))

    with Session.begin() as session:
        challenge: APIChallenge | None = (session.scalars(select(APIChallenge)
                                                          .filter(APIChallenge.discord_id == state))
                                          ).first()
        if challenge is None:
            return redirect(url_for('expired'))

        # Get OAuth token
        body = {
            'grant_type': 'authorization_code',
            'code': code,
            'code_verifier': challenge.code_verifier,
            'redirect_uri': os.getenv('CONNECT_REDIRECT_URI'),
            'client_id': os.getenv('CONNECT_CLIENT_ID')
        }
        resp = requests.post(url='https://lichess.org/api/token', json=body)
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            return redirect(url_for('error'))
        content = resp.json()

        # Check connected user data
        resp = requests.get(url='https://lichess.org/api/account',
                            headers={'Authorization': f'Bearer {content["access_token"]}'})
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            return redirect(url_for('error'))
        content = resp.json()
        username = content['id']
        try:
            puzzle_rating = content['perfs']['puzzle']['rating']
        except KeyError:
            puzzle_rating = None

        session.merge(User(discord_id=state, lichess_username=username, puzzle_rating=puzzle_rating))
        session.delete(challenge)

    flask.session['username'] = username
    return redirect(url_for('success'))


@app.errorhandler(HTTPException)
def handle_bad_request(e):
    return flask.render_template('exceptions.html', code=e.code, description=e.description.split('.')[0])


# uWSGI application
application = app
app.secret_key = os.getenv('FLASK_SECRET')
app.config['SESSION_TYPE'] = 'filesystem'

if __name__ == '__main__':
    app.config['SERVER_NAME'] = '192.168.50.200:5000'  # Development server
    application.run()

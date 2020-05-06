import requests
from bs4 import BeautifulSoup
import re
import discord

name = 'lichess.org/@/rohans1'
if match := re.match('(?:https://)?lichess\.org/@/([\S]+)', name):
    print(match.string)
    print(match.groups()[0])
response = requests.get(f'https://lichess.org/@/rohans1')
soup = BeautifulSoup(response.text, 'html.parser')
ratings = soup.find_all('rating')

for rating_tag in ratings[:4]:
    gamemode = rating_tag.find_parent('a').find('h3').string
    rating = rating_tag.find('strong').string
    n_games = rating_tag.find('span').string
    print(gamemode, rating, n_games)
    # rating_values = re.match(r'\d+', rating).groups()
    # print(rating_values)

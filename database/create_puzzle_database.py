import json
import re
import time
import mysql.connector
import requests
import sys
sys.stdout = open('./logs.txt', 'w')

try:
    connection = mysql.connector.connect(user='thijs',
                                         host='localhost',
                                         database='lichess')
except mysql.connector.Error as err:
    print(err)
    exit()

cursor = connection.cursor(buffered=True)
add_puzzle = ("INSERT INTO puzzles "
               "(puzzle_id, rating, color, answers, follow_up) "
               "VALUES (%s, %s, %s, %s, %s)")

start = time.time()
for puzzle_id in range(61326, 100001):
    secs_to_sleep = 1
    try:
        time.sleep(secs_to_sleep)
        print(puzzle_id, flush=True)
        response = requests.get(f'https://lichess.org/training/{puzzle_id}')
        while response.status_code == 429:  # Too many requests, wait a bit
            print("sleeping...", flush=True)
            secs_to_sleep += 14  # sleep a bit longer
            time.sleep(secs_to_sleep)
            response = requests.get(f'https://lichess.org/training/{puzzle_id}')
        pattern = re.compile(r"lichess\.puzzle = (.*)</script><script nonce")  # find puzzle json string
        json_txt = pattern.findall(response.text)[0]
        js = json.loads(json_txt)
        color = js['data']['puzzle']['color']
        puzzle_rating = js['data']['puzzle']['rating']

        move = js['data']['puzzle']['branch']
        answers = [move['san']]
        follow_ups = []

        other = True
        while 'children' in move:
            next_moves = move['children']
            if len(next_moves) == 0:  # No more moves
                break
            move = next_moves[0]
            if other:
                follow_ups.append(move['san'])
            else:
                answers.append(move['san'])
            other = not other

        data_puzzle = (int(puzzle_id), int(puzzle_rating), color, str(answers), str(follow_ups))
        cursor.execute(add_puzzle, data_puzzle)
        if puzzle_id % 25 == 0:
            connection.commit()
        if puzzle_id % 500 == 0:
            print(time.time()-start, 'seconds running')
    except:
        continue

connection.commit()

cursor.close()
connection.close()

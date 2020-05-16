import mysql.connector
import random
from bisect import bisect_left

try:
    connection = mysql.connector.connect(user='thijs',
                                         host='localhost',
                                         database='lichess')
except mysql.connector.Error as err:
    print(err)
    exit()

cursor = connection.cursor(buffered=True)
# 8634

cursor.execute("SELECT * FROM puzzles where rating between 100 and 800")
results = cursor.fetchall()
if len(results) == 0:
    print('Nope')
    exit()
else:
    puzzle_id, puzzle_rating, color, answers, follow_ups = random.choice(results)

print(puzzle_id, puzzle_rating, color, answers, follow_ups)


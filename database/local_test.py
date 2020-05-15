import mysql.connector
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

cursor.execute("SELECT * FROM puzzles where puzzle_id = 8634;")
ids = list(cursor.fetchall())
print(ids)

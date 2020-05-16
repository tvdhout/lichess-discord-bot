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

cursor.execute("SELECT * FROM puzzles where rating between 100 and 500")
results = cursor.fetchall()
print(results)



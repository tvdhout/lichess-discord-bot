import sys
from typing import List, Tuple
import mysql.connector
import lichess.api


def get_connected_users(connection: mysql.connector.MySQLConnection) -> List[Tuple[str]]:
    cursor = connection.cursor(buffered=True)
    cursor.execute("SELECT LichessName FROM users")
    lichess_names = cursor.fetchall()
    connection.commit()
    cursor.close()
    return lichess_names


def update_ratings(lichess_names: List[str], connection: mysql.connector.MySQLConnection) -> None:
    cursor = connection.cursor(buffered=True)
    for name in lichess_names:
        try:
            user = lichess.api.user(name)
            try:
                puzzle_rating = user['perfs']['puzzle']['rating']
            except KeyError:  # No puzzle rating found
                puzzle_rating = -1  # No rating
            cursor.execute("UPDATE users SET Rating = %s WHERE LichessName = %s",
                           (puzzle_rating, name))
        except lichess.api.ApiHttpError:  # User no longer exists
            cursor.execute("DELETE FROM users WHERE LichessName = %s",
                           (name,))
    connection.commit()
    cursor.close()


if __name__ == '__main__':
    try:
        db_connection = mysql.connector.connect(user='thijs', host='localhost', database='lichess')
        users = get_connected_users(connection=db_connection)
        users = list(map(lambda u: u[0], users))
        update_ratings(lichess_names=users, connection=db_connection)
    except mysql.connector.Error:
        print("Database connection error!", file=sys.stderr)

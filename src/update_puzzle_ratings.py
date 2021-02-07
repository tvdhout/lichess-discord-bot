import logging
import time
from typing import List, Tuple, Dict
import mysql.connector
import lichess.api


def get_connected_users(connection: mysql.connector.MySQLConnection) -> List[Tuple[str]]:
    start_time = time.time()
    cursor = connection.cursor(buffered=True)
    cursor.execute("SELECT LichessName FROM users")
    lichess_names = cursor.fetchall()
    connection.commit()
    cursor.close()
    stop_time = time.time()
    logger.info(f"Fetched {len(lichess_names)} lichess names from the database. ({round(stop_time-start_time, 3)} sec)")
    return lichess_names


def update_ratings(lichess_names: List[str], connection: mysql.connector.MySQLConnection) -> None:
    start_time = time.time()

    update_dict: Dict[str, int] = {}  # LichessName : new rating
    delete_data: List[Tuple[str]] = []  # Usernames to remove from database
    for name in lichess_names:
        try:
            user = lichess.api.user(name)
            try:
                puzzle_rating = user['perfs']['puzzle']['rating']
                update_dict[name] = puzzle_rating
            except KeyError:  # No puzzle rating found
                puzzle_rating = -1  # No rating
                update_dict[name] = puzzle_rating
        except lichess.api.ApiHttpError:  # User no longer exists
            delete_data.append((name,))

    update_data = list(update_dict.items())  # Turn dict into list of (key,value) tuples
    update_data = [(t[1], t[0]) for t in update_data]  # Change (name, rating) tuples to (rating, name)
    api_done_time = time.time()
    logger.info(f"Looked up new user ratings. Update {len(update_data)}, delete {len(delete_data)}. "
                f"({round(api_done_time-start_time, 3)} sec)")

    cursor = connection.cursor(buffered=True)
    cursor.executemany("UPDATE users SET Rating = %s WHERE LichessName = %s", update_data)
    cursor.executemany("DELETE FROM users WHERE LichessName = %s", delete_data)
    connection.commit()
    cursor.close()
    stop_time = time.time()
    logger.info(f"Updated database. ({round(stop_time-api_done_time, 3)} sec)")


def get_logger() -> logging.getLoggerClass():
    update_logger = logging.getLogger("UpdateRatings")
    update_logger.setLevel(logging.INFO)
    handler = logging.FileHandler("./UpdateRatings.log")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s", "%Y-%m-%d %H:%M")
    handler.setFormatter(formatter)
    update_logger.addHandler(handler)
    return update_logger


if __name__ == '__main__':
    logger = get_logger()
    logger.info("Starting updating sequence...")
    try:
        db_connection = mysql.connector.connect(user='thijs', host='localhost', database='lichess')
        users = get_connected_users(connection=db_connection)
        users = list(map(lambda u: u[0], users))
        update_ratings(lichess_names=users, connection=db_connection)
    except mysql.connector.Error as e:
        logger.exception(f"MySQL connection failed!\n{e}")
    logger.info("Done ----------------\n\n")

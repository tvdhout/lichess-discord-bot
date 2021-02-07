import time
from typing import List, Tuple, Dict
from discord.ext import commands, tasks
import lichess.api

from LichessBot import LichessBot


class Updater(commands.Cog):
    """
    Cog to update puzzle ratings of connected Lichess accounts every 12 hours.
    """
    def __init__(self, client: LichessBot):
        self.client = client
        self.logger = self.client.logger
        self.update_task.start()

    def get_connected_users(self) -> List[str]:
        start_time = time.time()
        cursor = self.client.connection.cursor(buffered=True)
        cursor.execute("SELECT LichessName FROM users")
        lichess_names = cursor.fetchall()
        self.client.connection.commit()
        cursor.close()
        stop_time = time.time()
        self.logger.debug(
            f"Fetched {len(lichess_names)} lichess names from the database. ({round(stop_time - start_time, 3)} sec)")
        lichess_names = list(map(lambda u: u[0], lichess_names))  # flatten tuples
        return lichess_names

    def update_ratings(self, lichess_names: List[str]) -> None:
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
        self.logger.debug(f"Looked up new user ratings. Update {len(update_data)}, delete {len(delete_data)}. "
                          f"({round(api_done_time - start_time, 3)} sec)")

        cursor = self.client.connection.cursor(buffered=True)
        cursor.executemany("UPDATE users SET Rating = %s WHERE LichessName = %s", update_data)
        cursor.executemany("DELETE FROM users WHERE LichessName = %s", delete_data)
        self.client.connection.commit()
        cursor.close()
        stop_time = time.time()
        self.logger.debug(f"Updated database. ({round(stop_time - api_done_time, 3)} sec)")

    @tasks.loop(hours=12)
    async def update_task(self):
        """
        Update puzzle ratings every 12 hours
        @return:
        """
        self.logger.info("Starting updating connected user ratings sequence...")
        users = self.get_connected_users()
        self.update_ratings(lichess_names=users)
        self.logger.info("Done updating connected user ratings.")


def setup(client: LichessBot):
    client.add_cog(Updater(client))
    client.logger.info("Sucessfully added cog: Rating updater")

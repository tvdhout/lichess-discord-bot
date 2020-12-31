import mysql.connector
from discord.ext.commands import Context


def connect(func):
    async def connection_wrapper(context: Context, **kwargs):
        try:  # Connect to database
            connection = mysql.connector.connect(user='thijs',
                                                 host='localhost',
                                                 database='lichess')
            cursor = connection.cursor(buffered=True)
            try:
                await func(context, cursor, **kwargs)
                connection.commit()
            except Exception as e:
                print(repr(e))
            finally:
                cursor.close()
                connection.disconnect()
        except mysql.connector.Error:
            await context.send("Oops! I can't connect to the puzzle database. If the problem persists, please let me "
                               "know by filing an issue in the bot support "
                               "server: https://discord.gg/xCpCRsp")
            print("Database connection error")

    return connection_wrapper

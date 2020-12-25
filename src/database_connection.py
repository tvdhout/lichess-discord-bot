import mysql.connector


def connect():
    try:  # Connect to database
        connection = mysql.connector.connect(user='thijs',
                                             host='localhost',
                                             database='lichess')
        return connection
    except mysql.connector.Error:
        return

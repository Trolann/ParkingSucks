import mysql.connector
from os import getenv
from dataclasses import dataclass
from datetime import timedelta, datetime
from api_log import BotLog

logger = BotLog('api-mariadb')
@dataclass
class Garage:
    name: str
    address: str
    fullness: int
    timestamp: str

    def get_tuple(self):
        return self.name, self.address, self.fullness, self.timestamp

# ... (previous code)
class Config:
    def __init__(self):
        # Try to connect to the MySQL server without an SSH tunnel
        self.conn = mysql.connector.connect(
            host=getenv("DB_HOST"),
            user=getenv("DB_USER"),
            password=getenv("DB_PASS"),
            database=getenv("DB_NAME"),
            port=getenv("DB_PORT")
            )

        if self.conn:
            logger.info(f'Connected to MariaDB host {getenv("DB_HOST")}')
        else:
            logger.error(f'Could not connect to MariaDB host {getenv("DB_HOST")}')
            self.__del__()

    def __del__(self):
        self.conn.close()

    def get_latest(self, table):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(f'SELECT * FROM {table} ORDER BY time DESC LIMIT 1;')
        try:
            result = cursor.fetchone()
        except Exception as e:
            logger.error(f'Could not get latest entry in {table}: {e}')
            return None
        logger.info(f'Found {len(result)} results for latest entry in {table}')
        return result

    def get_yesterday(self, table):
        cursor = self.conn.cursor(dictionary=True)
        time_yesterday = datetime.now() - timedelta(days=1)
        query = f"SELECT * FROM {table} WHERE time >= '{time_yesterday}' AND time < '{time_yesterday + timedelta(minutes=1)}' ORDER BY time DESC;"
        cursor.execute(query)
        try:
            results = cursor.fetchall()
        except Exception as e:
            logger.error(f'Could not get yesterday\'s entries in {table}: {e}')
            return None
        logger.info(f'Found {len(results)} results for yesterday in {table}')
        return results

    def get_last_week(self, table):
        cursor = self.conn.cursor(dictionary=True)
        time_last_week = datetime.now() - timedelta(weeks=1)
        query = f"SELECT * FROM {table} WHERE time >= '{time_last_week}' AND time < '{time_last_week + timedelta(minutes=1)}' ORDER BY time DESC;"
        cursor.execute(query)
        try:
            results = cursor.fetchall()
        except Exception as e:
            logger.error(f'Could not get last week\'s entries in {table}: {e}')
            return None
        logger.info(f'Found {len(results)} results for last week in {table}')
        return results

    def run_query(self, sql_query):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(sql_query)
        try:
            results = cursor.fetchall()
        except Exception as e:
            logger.error(f'Could not run query {sql_query}: {e}')
            return None
        logger.info(f'Found {len(results)} results for query {sql_query}')
        return results

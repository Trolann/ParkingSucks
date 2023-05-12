from time import sleep
import pymysql
from os import getenv
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import hashlib
import newrelic.agent
from completion_log import BotLog

# Instantiating a new logger object with the name 'mariadb'
logger = BotLog('completion-mariadb')

CLEANUP_SLEEP = 60*60*12  # 12 hours

class Memory:
    def __init__(self):
        self.conn = None
        self.table = getenv("USER_DB_TABLE")
        self.fernet = Fernet(getenv("USER_DB_KEY"))
        self.retry_connection()

    def _hash_username(self, username):
        return hashlib.sha256(username.encode()).hexdigest()

    @newrelic.agent.background_task()
    def retry_connection(self, max_retries=3, delay=5):
        retries = 0
        while retries < max_retries:
            try:
                self.conn = pymysql.connect(
                    host=getenv("USER_DB_HOST"),
                    user=getenv("USER_DB_USER"),
                    password=getenv("USER_DB_PASS"),
                    db=getenv("USER_DB_NAME"),
                    port=int(getenv("USER_DB_PORT"))
                )
                if self.conn:
                    logger.info(f'Connected to MariaDB host {getenv("USER_DB_HOST")}')
                    return
            except Exception as e:
                logger.error(f'Could not connect to MariaDB host {getenv("USER_DB_HOST")}: {e}')
                sleep(delay)
                retries += 1

        logger.error(f'Failed to connect to MariaDB host {getenv("USER_DB_HOST")} after {max_retries} retries')

    @newrelic.agent.background_task()
    def write_schedule(self, username, schedule):
        username_hashed = self._hash_username(username)
        username_encrypted = self.fernet.encrypt(username.encode()).decode()
        schedule_encrypted = self.fernet.encrypt(schedule.encode()).decode()
        with self.conn.cursor() as cursor:
            query = f"""
                    INSERT INTO {self.table} (username_hashed, username, schedule, dateadded)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        username = VALUES(username),
                        schedule = VALUES(schedule),
                        dateadded = VALUES(dateadded)
                """
            try:
                cursor.execute(query, (username_hashed, username_encrypted, schedule_encrypted, datetime.now()))
                self.conn.commit()
                logger.info(f"Inserted or updated schedule for user '{username}'")
            except Exception as e:
                logger.error(f"Failed to insert or update schedule for user '{username}': {e}")

    @newrelic.agent.background_task()
    def get_schedule(self, username):
        username_hashed = self._hash_username(username)
        with self.conn.cursor() as cursor:
            query = f"""
                SELECT username, schedule, dateadded FROM {self.table}
                WHERE username_hashed = %s
            """
            schedule = None
            try:
                cursor.execute(query, (username_hashed,))
                result = cursor.fetchone()
                if result:
                    _username, schedule_encrypted, date_added = result
                    try:
                        # Set the ttl to 6 months (in seconds)
                        ttl = 6 * 30 * 24 * 60 * 60
                        schedule = self.fernet.decrypt(schedule_encrypted.encode(), ttl=ttl).decode()
                    except Exception as e:
                        logger.error(f"Failed to fetch schedule for user '{username}': {e}")
                else:
                    logger.info(f"No schedule found for user '{username}'.")
            except Exception as e:
                logger.error(f"Failed to fetch schedule for user '{username}': {e}")

        return schedule if schedule else ''

    @newrelic.agent.background_task()
    def delete_schedule(self, username_hashed):
        with self.conn.cursor() as cursor:
            query = f"""
                DELETE FROM {self.table}
                WHERE username_hashed = %s
            """
            try:
                cursor.execute(query, (username_hashed,))
                self.conn.commit()
                logger.info("Deleted schedule due to expiration or token issues")
            except Exception as e:
                logger.error(f"Failed to delete schedule: {e}")

    @newrelic.agent.background_task()
    def cleanup_old_records(self):
        with self.conn.cursor() as cursor:
            query = f"""
                DELETE FROM {self.table}
                WHERE dateadded < %s
            """
            try:
                cursor.execute(query, (datetime.now() - timedelta(days=125),))
                self.conn.commit()
                logger.info("Cleaned up old records")
            except Exception as e:
                logger.error(f"Failed to clean up old records: {e}")

    def cleanup_scheduler(self, interval):
        while True:
            self.cleanup_old_records()
            sleep(interval)

    def __del__(self):
        self.conn.close()
# I need the SQL command to update the user 'completions' and allow it to have connections from the 172.18.x.x subnet

# write a SQL query to select for each unique 'name' in a table the row with the most recent 'time'

# Change this query:
# SELECT t1.* FROM {table} t1 INNER JOIN (SELECT name, MAX(time) AS max_time FROM {table} GROUP BY name) t2 ON t1.name = t2.name AND t1.time = t2.max_time;
#
# To select the average of this time last week -30 minutes. So if now is noon on Monday April 17, this would select the average time for each unique name between 1130am and 12pm on April 10th.

# I want to add a '%' after each integer in the 'fullness' column

# At the end of this query I want to concat a row which reads:
# Average information for day around time

# I want a MariaDB SQL query which will return the name and fullness of each unique name based on this criteria:
# - Given a day (Monday/Tuesday/Wednesday) and a time (HH:MM:SS) search through all 'time' values for the given day between (time - 60 minutes) and time
# - For each unique name, average the values
# - Return 2 columns: name and fullness
# - Return 1 unique row per unique name in the table
# - Append to the end of the results a row which reads:
# Average fullness for day at time





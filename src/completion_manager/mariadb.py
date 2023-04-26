import asyncio
import aiomysql
from os import getenv
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import newrelic.agent
from completion_log import BotLog

# Instantiating a new logger object with the name 'mariadb'
logger = BotLog('completion-mariadb')

CLEANUP_SLEEP = 60*60*12  # 12 hours

class Config:
    def __init__(self):
        self.conn = None
        self.table = getenv("USER_DB_TABLE")
        self.fernet = Fernet(getenv("USER_DB_KEY"))
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.retry_connection())
        self.loop.create_task(self.cleanup_scheduler(CLEANUP_SLEEP))

    @newrelic.agent.background_task()
    async def retry_connection(self, max_retries=3, delay=5):
        retries = 0
        while retries < max_retries:
            try:
                self.conn = await aiomysql.connect(
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
                await asyncio.sleep(delay)
                retries += 1

        logger.error(f'Failed to connect to MariaDB host {getenv("USER_DB_HOST")} after {max_retries} retries')

    @newrelic.agent.background_task()
    async def write_schedule(self, username, schedule):
        username_encrypted = self.fernet.encrypt(username.encode()).decode()
        schedule_encrypted = self.fernet.encrypt(schedule.encode()).decode()
        async with self.conn.cursor() as cursor:
            query = f"""
                    INSERT INTO {self.table} (username, schedule, dateadded)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        schedule = VALUES(schedule),
                        dateadded = VALUES(dateadded)
                """
            try:
                await cursor.execute(query, (username_encrypted, schedule_encrypted, datetime.now()))
                await self.conn.commit()
                logger.info(f"Inserted or updated schedule for user '{username}'")
            except Exception as e:
                logger.error(f"Failed to insert or update schedule for user '{username}': {e}")

    @newrelic.agent.background_task()
    async def get_schedule(self, username):
        username_encrypted = self.fernet.encrypt(username.encode()).decode()
        async with self.conn.cursor() as cursor:
            query = f"""
                SELECT schedule, dateadded FROM {self.table}
                WHERE username = %s
            """
            schedule = None
            try:
                await cursor.execute(query, (username_encrypted,))
                result = await cursor.fetchone()
                if result:
                    schedule_encrypted, date_added = result
                    try:
                        # Set the ttl to 6 months (in seconds)
                        ttl = 6 * 30 * 24 * 60 * 60
                        schedule = self.fernet.decrypt(schedule_encrypted.encode(), ttl=ttl).decode()
                    except Exception as e:
                        logger.error(f"Failed to decrypt schedule for user '{username}': {e}")
                        await self.delete_schedule(username_encrypted)
                else:
                    logger.info(f"No schedule found for user '{username}'.")
            except Exception as e:
                logger.error(f"Failed to fetch schedule for user '{username}': {e}")

        return schedule if schedule else 'No schedule for the user. This might be their first time here.'

    @newrelic.agent.background_task()
    async def delete_schedule(self, username_encrypted):
        async with self.conn.cursor() as cursor:
            query = f"""
                DELETE FROM {self.table}
                WHERE username = %s
            """
            try:
                await cursor.execute(query, (username_encrypted,))
                await self.conn.commit()
                logger.info("Deleted schedule due to expiration or token issues")
            except Exception as e:
                logger.error(f"Failed to delete schedule: {e}")

    @newrelic.agent.background_task()
    async def cleanup_old_records(self):
        async with self.conn.cursor() as cursor:
            query = f"""
                DELETE FROM {self.table}
                WHERE dateadded < %s
            """
            try:
                await cursor.execute(query, (datetime.now() - timedelta(days=125),))
                await self.conn.commit()
                logger.info("Cleaned up old records")
            except Exception as e:
                logger.error(f"Failed to clean up old records: {e}")

    async def cleanup_scheduler(self, interval):
        while True:
            await self.cleanup_old_records()
            await asyncio.sleep(interval)

    def __del__(self):
        self.conn.close()


user_db = Config()

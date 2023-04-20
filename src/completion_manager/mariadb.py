import mysql.connector
from os import getenv
from time import sleep
from datetime import datetime, timedelta
import threading
from completion_log import BotLog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from base64 import urlsafe_b64encode, urlsafe_b64decode

# Instantiating a new logger object with the name 'mariadb'
logger = BotLog('completion-mariadb')

CLEANUP_SLEEP = 60*60  # 1 hour


def init_fernet():
    fernet_key = getenv("FERNET_KEY")

    if fernet_key is None:
        fernet_key = Fernet.generate_key()
        with open("logs/fernet.env", "wb") as f:
            f.write(fernet_key)

    return Fernet(fernet_key)


class Config:
    def __init__(self):
        self.conn = None
        self.table = getenv("USER_DB_TABLE")
        self.fernet = init_fernet()
        self.retry_connection()

    def retry_connection(self, max_retries=3, delay=5):
        retries = 0
        while retries < max_retries:
            try:
                self.conn = mysql.connector.connect(
                    host=getenv("USER_DB_HOST"),
                    user=getenv("USER_DB_USER"),
                    password=getenv("USER_DB_PASS"),
                    database=getenv("USER_DB_NAME"),
                    port=getenv("USER_DB_PORT")
                )
                if self.conn:
                    logger.info(f'Connected to MariaDB host {getenv("USER_DB_HOST")}')
                    cleanup_interval = CLEANUP_SLEEP  # 1 hour
                    cleanup_thread = threading.Thread(target=self.cleanup_scheduler, args=(cleanup_interval,), daemon=True)
                    cleanup_thread.start()
            except Exception as e:
                logger.error(f'Could not connect to MariaDB host {getenv("USER_DB_HOST")}: {e}')
                sleep(delay)
                retries += 1

        logger.error(f'Failed to connect to MariaDB host {getenv("USER_DB_HOST")} after {max_retries} retries')
        self.__del__()

    def insert_or_update(self, username, schedule):
        username_encrypted = self.fernet.encrypt(username.encode()).decode()
        schedule_encrypted = self.fernet.encrypt(schedule.encode()).decode()
        cursor = self.conn.cursor()
        query = f"""
            INSERT INTO {self.table} (username, schedule, dateadded)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                schedule = VALUES(schedule),
                dateadded = VALUES(dateadded)
        """
        try:
            cursor.execute(query, (username_encrypted, schedule_encrypted, datetime.now()))
            self.conn.commit()
            logger.info(f"Inserted or updated schedule for user '{username}'")
        except Exception as e:
            logger.error(f"Failed to insert or update schedule for user '{username}': {e}")
        finally:
            cursor.close()

    def get_schedule(self, username):
        username_encrypted = self.fernet.encrypt(username.encode()).decode()
        cursor = self.conn.cursor()
        query = f"""
            SELECT schedule, dateadded FROM {self.table}
            WHERE username = %s
        """
        schedule = None
        try:
            cursor.execute(query, (username_encrypted,))
            result = cursor.fetchone()
            if result:
                schedule_encrypted, date_added = result
                try:
                    # Set the ttl to 6 months (in seconds)
                    ttl = 6 * 30 * 24 * 60 * 60
                    schedule = self.fernet.decrypt(schedule_encrypted.encode(), ttl=ttl).decode()
                except Exception as e:
                    logger.error(f"Failed to decrypt schedule for user '{username}': {e}")
                    self.delete_schedule(username_encrypted)
            else:
                logger.info(f"No schedule found for user '{username}'")
        except Exception as e:
            logger.error(f"Failed to fetch schedule for user '{username}': {e}")
        finally:
            cursor.close()

        return schedule

    def delete_schedule(self, username_encrypted):
        cursor = self.conn.cursor()
        query = f"""
            DELETE FROM {self.table}
            WHERE username = %s
        """
        try:
            cursor.execute(query, (username_encrypted,))
            self.conn.commit()
            logger.info("Deleted schedule due to expiration or token issues")
        except Exception as e:
            logger.error(f"Failed to delete schedule: {e}")
        finally:
            cursor.close()

    def cleanup_old_records(self):
        cursor = self.conn.cursor()
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
        finally:
            cursor.close()

    def cleanup_scheduler(self, interval):
        while True:
            self.cleanup_old_records()
            sleep(interval)

    def __del__(self):
        self.conn.close()

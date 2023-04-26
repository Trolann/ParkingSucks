import mysql.connector
from os import getenv
from datetime import timedelta, datetime
from api_log import BotLog
from time import sleep

logger = BotLog('api-mariadb')

class Config:
    def __init__(self):
        self.conn = None
        self.retry_connection()

    def retry_connection(self, max_retries=3, delay=5):
        retries = 0
        while retries < max_retries:
            try:
                self.conn = mysql.connector.connect(
                    host=getenv("DB_HOST"),
                    user=getenv("DB_USER"),
                    password=getenv("DB_PASS"),
                    database=getenv("DB_NAME"),
                    port=getenv("DB_PORT")
                )
                if self.conn:
                    logger.info(f'Connected to MariaDB host {getenv("DB_HOST")}')
                    return
            except Exception as e:
                logger.error(f'Could not connect to MariaDB host {getenv("DB_HOST")}: {e}')
                sleep(delay)
                retries += 1

        logger.error(f'Failed to connect to MariaDB host {getenv("DB_HOST")} after {max_retries} retries')
        self.__del__()

    def __del__(self):
        self.conn.close()

    def get_cursor(self):
        try:
            cursor = self.conn.cursor(dictionary=True)
        except Exception as e:
            if 'MySQL Connection not available' in str(e):
                self.retry_connection()
                cursor = self.conn.cursor(dictionary=True)
            else:
                logger.error(f"Could not create cursor for {getenv('DB_HOST')}: {e}")
                return None
        return cursor

    def get_latest(self, table, shuttle=False):
        cursor = self.get_cursor()
        cursor.execute(f'''
            WITH latest_time AS (
                SELECT name, MAX(time) AS most_recent_time
                FROM `{table}`
                GROUP BY name
            )
            SELECT CONCAT(t.fullness, '%') AS fullness, lt.name
            FROM latest_time lt
            JOIN `{table}` t ON lt.name = t.name AND lt.most_recent_time = t.time
            UNION ALL
            SELECT NULL AS fullness, CONCAT('Data above is current through the most recent time: ', MAX(lt.most_recent_time)) AS name
            FROM latest_time lt;
        ''' if not shuttle else f'''
            WITH latest_time AS (
                SELECT stop_name, MAX(updated_at) AS most_recent_time
                FROM `{table}`
                GROUP BY stop_name
            )
            SELECT CONCAT(t.time_to_departure, ' minutes') AS time_to_departure, lt.stop_name
            FROM latest_time lt
            JOIN `{table}` t ON lt.stop_name = t.stop_name AND lt.most_recent_time = t.updated_at
            UNION ALL
            SELECT NULL AS time_to_departure, CONCAT('Data above is current through the most recent time: ', MAX(lt.most_recent_time)) AS stop_name
            FROM latest_time lt;
            ''')
        try:
            result = cursor.fetchall()
            print(result)
        except Exception as e:
            logger.error(f'Could not get latest entry in {table}: {e}')
            return None
        num_results = len(result) if result else 0
        logger.info(f'Found {num_results} results for latest entry in {table}')
        return result

    def get_yesterday(self, table, shuttle=False):
        cursor = self.get_cursor()
        time_last_week = datetime.now() - timedelta(weeks=1)
        query = f'''
            SELECT CONCAT(CEILING(AVG(fullness)), '%') AS avg_fullness, name
            FROM `{table}`
            WHERE time >= DATE_ADD(NOW(), INTERVAL -1 DAY) - INTERVAL 30 MINUTE
            AND time < DATE_ADD(NOW(), INTERVAL -1 DAY) + INTERVAL 30 MINUTE
            GROUP BY name
            UNION ALL
            
            SELECT CONCAT('Data above is for ', 
                  DATE_ADD(NOW(), INTERVAL -1 DAY) - INTERVAL 30 MINUTE,
                  ' to ', 
                  DATE_ADD(NOW(), INTERVAL -1 DAY) + INTERVAL 30 MINUTE
                 ) AS message, '' AS name;
        ''' if not shuttle else f'''
            SELECT CONCAT(CEILING(AVG(time_to_departure)), ' minutes') AS avg_time_to_departure, stop_name
            FROM `{table}`
            WHERE updated_at >= DATE_ADD(NOW(), INTERVAL -1 DAY) - INTERVAL 30 MINUTE
            AND updated_at < DATE_ADD(NOW(), INTERVAL -1 DAY) + INTERVAL 30 MINUTE
            GROUP BY stop_name
            UNION ALL
            
            SELECT CONCAT('Data above is for ',
                  DATE_ADD(NOW(), INTERVAL -1 DAY) - INTERVAL 30 MINUTE,
                  ' to ',
                  DATE_ADD(NOW(), INTERVAL -1 DAY) + INTERVAL 30 MINUTE
                 ) AS message, '' AS stop_name;
        '''
        cursor.execute(query)
        try:
            results = cursor.fetchall()
        except Exception as e:
            logger.error(f'Could not get last week\'s entries in {table}: {e}')
            return None
        logger.info(f'Found {len(results)} results for last week in {table}')
        return results

    def get_last_week(self, table, shuttle=False):
        cursor = self.get_cursor()

        query = f'''
            SELECT CONCAT(CEILING(AVG(fullness)), '%') AS avg_fullness, name
            FROM `{table}`
            WHERE time >= DATE_ADD(NOW(), INTERVAL -168 HOUR) - INTERVAL 30 MINUTE
            AND time < DATE_ADD(NOW(), INTERVAL -168 HOUR)
            GROUP BY name
            UNION ALL
            
            SELECT CONCAT('Data above is for ', 
                  DATE_ADD(DATE_ADD(NOW(), INTERVAL -168 HOUR), INTERVAL -30 MINUTE),
                  ' to ', 
                  DATE_ADD(NOW(), INTERVAL -168 HOUR)
                 ) AS message, '' AS name;
        ''' if not shuttle else f'''
            SELECT CONCAT(CEILING(AVG(time_to_departure)), ' minutes') AS avg_time_to_departure, stop_name
            FROM `{table}`
            WHERE updated_at >= DATE_ADD(NOW(), INTERVAL -168 HOUR) - INTERVAL 30 MINUTE
            AND updated_at < DATE_ADD(NOW(), INTERVAL -168 HOUR)
            GROUP BY stop_name
            UNION ALL
            
            SELECT CONCAT('Data above is for ', 
                  DATE_ADD(DATE_ADD(NOW(), INTERVAL -168 HOUR), INTERVAL -30 MINUTE),
                  ' to ', 
                  DATE_ADD(NOW(), INTERVAL -168 HOUR)
                 ) AS message, '' AS stop_name;
        '''
        cursor.execute(query)
        try:
            results = cursor.fetchall()
            print(results)
        except Exception as e:
            logger.error(f'Could not get yesterday\'s entries in {table}: {e}')
            return None
        logger.info(f'Found {len(results)} results for yesterday in {table}')
        return results

    def get_average(self, table, day, time, shuttle=False):
        cursor = self.get_cursor()
        query = f"""
            SELECT name, CONCAT(CEILING(AVG(fullness)), '%') AS fullness
            FROM `{table}`
            WHERE DAYNAME(time) = '{day}'
              AND TIME(time) BETWEEN ADDTIME('{time}', '-01:00:00') AND '{time}'
            GROUP BY name
            WITH ROLLUP
            
            UNION ALL
            
            SELECT CONCAT('Data above is average fullness for ', '{day}', ' at ', '{time}') AS name, CONCAT(CEILING(AVG(fullness)), '%') AS fullness
            FROM `{table}`
            WHERE DAYNAME(time) = '{day}'
              AND TIME(time) BETWEEN ADDTIME('{time}', '-01:00:00') AND '{time}'

        """ if not shuttle else f"""
            SELECT stop_name, CONCAT(CEILING(AVG(time_to_departure)), ' minutes') AS average_time_to_departure
            FROM `{table}`
            WHERE DAYNAME(updated_at) = '{day}'
            AND TIME(updated_at) BETWEEN ADDTIME('{time}', '-01:00:00') AND '{time}'
            GROUP BY stop_name
            WITH ROLLUP
            
            UNION ALL
            
            SELECT CONCAT('Data above is average time to departure for ', '{day}', ' at ', '{time}') AS stop_name, CONCAT(CEILING(AVG(time_to_departure)), ' minutes') AS average_time_to_departure
            FROM `{table}`
            WHERE DAYNAME(updated_at) = '{day}'
            AND TIME(updated_at) BETWEEN ADDTIME('{time}', '-01:00:00') AND '{time}'
        """
        cursor.execute(query)
        try:
            results = cursor.fetchall()
            print(results)
        except Exception as e:
            logger.error(f'Could not get average fullness for {table}: {e}')
            return None
        logger.info(f'Found {len(results)} results for {day} at {time} in {table}')
        return results

    def run_query(self, sql_query):
        cursor = self.get_cursor()
        cursor.execute(sql_query)
        try:
            results = cursor.fetchall()
        except Exception as e:
            logger.error(f'Could not run query {sql_query}: {e}')
            return None
        logger.info(f'Found {len(results)} results for query {sql_query}')
        return results

# Prompt 1:
# This MariaDB (10.10) class sometimes throws this error:
# [ERROR][api]: Error getting latest data: MySQL Connection not available.
#
# Update the class to try and get a new connection before throwing the exception. Ensure to log an error if needed.
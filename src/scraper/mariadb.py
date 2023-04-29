import mysql.connector
from os import getenv
from garage import Garage
from shuttle_scrapy import ShuttleStatus
from scraper_log import BotLog
import newrelic.agent

# Instantiating a new logger object with the name 'mariadb'
logger = BotLog('mariadb')

class Parking:
    """
    This class handles the configuration for the MySQL database. It has methods to create a table, load the latest data
    and add new data to the table.
    """
    def __init__(self, table_name) -> None:
        """
        The constructor for the Config class. It initializes the connection to the MySQL server and sets the table name.
        It then calls the create_table and load_latest methods.
        :param table_name: (str) The name of the table to be used in the MySQL server.
        """
        # Try to connect to the MySQL server without an SSH tunnel
        self.conn = mysql.connector.connect(
            host=getenv("DB_HOST"),
            user=getenv("DB_USER"),
            password=getenv("DB_PASS"),
            database=getenv("DB_NAME"),
            port=getenv("DB_PORT")
            )

        # Set the table name
        self.table = table_name

        # Not needed in current config, but low effort and could be useful in the future
        self.latest = self.load_latest()

    def load_latest(self) -> list:
        """
        This method loads the latest data from the MySQL server and returns it as a list of Garage objects.
        :return: (list) A list of Garage objects containing the latest data.
        """
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT t1.*
            FROM `{self.table}` t1
            JOIN (
                SELECT `name`, MAX(`time`) AS max_time
                FROM `{self.table}`
                GROUP BY `name`
            ) t2
            ON t1.`name` = t2.`name` AND t1.`time` = t2.max_time
        """)
        data = cursor.fetchall()
        cursor.close()
        return_list = []
        for id, name, address, fullness, timestamp in data:
            g = Garage(name, address, fullness, timestamp)
            return_list.append(g)
        if return_list:
            logger.debug(f"Loaded latest data from {self.table}")
        else:
            logger.error(f"Failed to load latest data from {self.table}")
        return return_list

    @newrelic.agent.background_task()
    def new(self, g: Garage) -> bool:
        """
        This method adds a new Garage object to the MySQL server if it meets certain criteria.
        :param g: (Garage) The Garage object to be added to the MySQL server.
        """
        with self.conn.cursor() as cursor:
            query = """
                INSERT INTO {table} (name, address, fullness, time)
                SELECT %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM {table}
                    WHERE name = %s AND time >= %s
                )
            """.format(table=self.table)
            # Keep the .config safe, log the error and return
            try:
                cursor.execute(query, (g.name, g.address, g.fullness, g.timestamp, g.name, g.timestamp))
                self.conn.commit()
                logger.debug(f'Added new data to {self.table}')
                self.config = self.load_latest()
                return True
            except Exception as err:
                logger.error(f"Failed to add new data to {self.table}: {err}")
                return False


    def __del__(self) -> None:
        """
        This method is called when the Config object is destroyed. It closes the connection to the MySQL server.
        """
        self.conn.close()

class Shuttles:
    """
    A connection to the Shuttle DB
    """
    def __init__(self, table_name) -> None:
        """
        The constructor for the Config class. It initializes the connection to the MySQL server and sets the table name.
        It then calls the create_table and load_latest methods.
        :param table_name: (str) The name of the table to be used in the MySQL server.
        """
        # Try to connect to the MySQL server without an SSH tunnel
        self.conn = mysql.connector.connect(
            host=getenv("DB_HOST"),
            user=getenv("DB_USER"),
            password=getenv("DB_PASS"),
            database=getenv("DB_NAME"),
            port=getenv("DB_PORT")
            )

        # Set the table name
        self.table = table_name

    @newrelic.agent.background_task()
    def insert_data(self, stop_name, time_to_departure, updated_at):
        """
        Inserts data into the table

        :param stop_name:
        :param time_to_departure:
        :param updated_at:
        :return:
        """
        cursor = self.conn.cursor()

        # Perform calculations for the day_of_week, hour_of_day, and rounded_time_to_departure
        day_of_week = updated_at.strftime('%A')
        hour_of_day = updated_at.hour
        rounded_time_to_departure = (time_to_departure // 5) * 5

        # Insert data into the sjsu-shuttles table
        insert_data_query = f"INSERT INTO `{self.table}` (stop_name, time_to_departure, updated_at, day_of_week, hour_of_day, rounded_time_to_departure) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_data_query, (stop_name, time_to_departure, updated_at, day_of_week, hour_of_day, rounded_time_to_departure))
        self.conn.commit()

        cursor.close()

    def get_latest_shuttle_statuses(self):
        """
        Gets the latest shuttle statuses from the table
        :return:
        """
        cursor = self.conn.cursor()
        query = f"""
            SELECT stop_name, time_to_departure, updated_at
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY stop_name ORDER BY updated_at DESC) AS row_num
                FROM `{self.table}`
            ) AS temp
            WHERE row_num = 1
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()

        shuttle_statuses = [ShuttleStatus(stop_name=row[0], time_to_departure=row[1], updated_at=row[2]) for row in
                            rows]
        return shuttle_statuses

garage_db = Parking('sjsu')
shuttles_db = Shuttles('sjsu-shuttles')

if __name__ == '__main__':
    config = Parking('test')


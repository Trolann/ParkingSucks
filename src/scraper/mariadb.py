import mysql.connector
from os import getenv
from garage import Garage
from scraper_log import BotLog

# Instantiating a new logger object with the name 'mariadb'
logger = BotLog('mariadb')

class Config:
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

        # Create the table if it doesn't already exist
        self.create_table()

        # Not needed in current config, but low effort and could be useful in the future
        self.latest = self.load_latest()

    def create_table(self) -> str:
        """
        This method creates the table in the MySQL server if it doesn't already exist.
        """
        cursor = self.conn.cursor()
        query = """
            CREATE TABLE IF NOT EXISTS %s (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `name` TEXT NOT NULL,
                `address` TEXT NOT NULL,
                `fullness` INT NOT NULL,
                `time` DATETIME NOT NULL
            )
        """
        cursor.execute(query % self.table)
        self.conn.commit()
        cursor.close()

        # To programatically get the schema of the table for an LLM later if needed
        if cursor.rowcount == 0:
            logger.info(f"Table {self.table} already exists")
            return query
        else:
            logger.info(f"Created table {self.table}")
            return "Created table"
        # Prompt: I want this to return a string of the query if the table exists and 'Created table' if it does not exist

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
            logger.info(f"Loaded latest data from {self.table}")
        else:
            logger.error(f"Failed to load latest data from {self.table}")
        return return_list

    def new(self, g: Garage) -> None:
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
            except Exception as err:
                logger.error(f"Failed to add new data to {self.table}: {err}")


    def __del__(self) -> None:
        """
        This method is called when the Config object is destroyed. It closes the connection to the MySQL server.
        """
        self.conn.close()

if __name__ == '__main__':
    config = Config('test')
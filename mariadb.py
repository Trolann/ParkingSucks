import mysql.connector
from os import getenv
from garage import Garage

class Config:
    def __init__(self, table_name):
        self.conn = mysql.connector.connect(
            host=getenv("DB_HOST"),
            user=getenv("DB_USER"),
            #=getenv("DB_PASS"),
            database=getenv("DB_NAME"),
            port=getenv("DB_PORT"),
        )
        self.table = table_name
        self.create_table()
        self.latest = self.load_latest()

    def create_table(self):
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

    def load_latest(self):
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
        #print('RETURN LIST')
        #print(return_list)
        return return_list

    def new(self, g: Garage):
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
            cursor.execute(query, (g.name, g.address, g.fullness, g.timestamp, g.name, g.timestamp))
            self.conn.commit()
        self.config = self.load_latest()

    def __del__(self):
        self.conn.close()

if __name__ == '__main__':
    config = Config('test')

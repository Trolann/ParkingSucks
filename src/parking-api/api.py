from quart import Quart, request, jsonify
from api_log import BotLog
import os
from mariadb import Config
from datetime import datetime

app = Quart(__name__)
logger = BotLog('api')
db = Config()


def valid_api_key(reqest: request) -> bool:
    """
    Check if the API key is valid.
    """
    api_key = request.args.get('api_key')
    if api_key != os.environ.get('API_KEY'):
        logger.error(f'Invalid API key from {request.remote_addr}')
        logger.error(f'Given API key: {api_key}')
        return False
    return True

@app.route('/latest')
def get_latest():
    """
    This route returns the latest data from a specified table in the database.
    """
    if valid_api_key(request):
        # We have a valid API key, allow for custom SQL parameters (extract them here)
        pass

    logger.info(f'Got API request for latest data from {request.remote_addr}')
    table = request.args.get('table')
    try:
        result = db.get_latest(table)
    except Exception as e:
        logger.error(f'Error getting latest data: {e}')
        return jsonify({"error": f"Error getting latest data"}), 500
    return jsonify(result)

@app.route('/yesterday')
def get_yesterday():
    """
    This route returns yesterday's data from a specified table in the database.
    """
    if valid_api_key(request):
        # We have a valid API key, allow for custom SQL parameters (extract them here)
        pass

    logger.info(f'Got API request for latest data from {request.remote_addr}')
    table = request.args.get('table')
    try:
        results = db.get_yesterday(table)
    except Exception as e:
        logger.error(f'Error getting latest data: {e}')
        return jsonify({"error": f"Error getting yesterday's data"}), 500

    return jsonify(results)

@app.route('/lastweek')
def get_last_week():
    """
    This route returns data from the last week from a specified table in the database.
    """
    if valid_api_key(request):
        # We have a valid API key, allow for custom SQL parameters (extract them here)
        pass
    logger.info(f'Got API request for yesterday\'s data from {request.remote_addr}')
    table = request.args.get('table')
    try:
        results = db.get_last_week(table)
    except Exception as e:
        logger.error(f'Error getting latest data: {e}')
        return jsonify({"error": f"Error getting latest data"}), 500
    return jsonify(results)

# TODO: Implement semesters
@app.route('/average')
def get_average():
    """
    This route returns the average fullness of a specified day of the week for the current semester.
    :return:
    """
    if valid_api_key(request):
        # We have a valid API key, allow for custom SQL parameters (extract them here)
        pass
    logger.info(f'Got API request for average fullness from {request.remote_addr}')
    table = request.args.get('table')
    day = request.args.get('day')
    time = request.args.get('time')
    # convert time to datetime
    time = datetime.strptime(time, '%H:%M:%S').time()
    try:
        results = db.get_average(table, day, time)
    except Exception as e:
        logger.error(f'Error getting average fullness: {e}')
        return jsonify({"error": f"Error getting average fullness"}), 500
    return jsonify(results)

@app.route('/query')
def run_query():
    """
    This route runs a specified SQL query on the database and returns the results.
    """
    if not valid_api_key(request):
        return jsonify({"error": "Invalid API Key"}), 401

    logger.info(f'Got API request to run query {request.remote_addr}')
    logger.info(f'Query: {request.args.get("query")}')
    sql_query = request.args.get('query')
    # Run query
    try:
        results = db.run_query(sql_query)
    except Exception as e:
        logger.error(f'Error running query: {e}')
        return jsonify({"error": f"Error running query"}), 500

    logger.info(f'Found {len(results)} results')
    return_val = ''

    # Format results into a string
    for item in results:
        parking_info = item.get('parking_info', '')
        if parking_info:
            return_val += parking_info + '\n'
    logger.info(f'Results: {return_val}')
    return jsonify(return_val)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# Prompt 1:
# We're making a flask API to query a database and return the results in a JSON format.
# Here's the schema for each table:
#             CREATE TABLE IF NOT EXISTS %s (
#                 `id` INT AUTO_INCREMENT PRIMARY KEY,
#                 `name` TEXT NOT NULL,
#                 `address` TEXT NOT NULL,
#                 `fullness` INT NOT NULL,
#                 `time` DATETIME NOT NULL
# Endpoints:
# /latest - gets the latest parking data
# /yesterday - gets the data from this time yesterday
# /lastweek - gets the data from this time last week
# /query - takes in 2 parameters: an api get and a SQL query. Runs the SQL query and returns the results.
# Generate api.py, requirements.txt and Dockerfile

# Prompt 2:
# <Gave code>
#Update this api.py file to use this mariadb.py file.
# Move SQL related functions and commands to the mariadb.py file and leave API
# commands and calls to the mariadb.py file in the api.py file. There should be 1 connection
# to the database which is used by all of the endpoints and each endpoint will pass the table to query.

# Prompt 3:
# this is close, but in this config all of them will use the same table (parking) and
# not the given argument table. Correct it.
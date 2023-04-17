from flask import Flask, request, jsonify
from api_log import BotLog
import os
from mariadb import Config

app = Flask(__name__)
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

# TODO: Broken query
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
        return jsonify({"error": f"Error getting latest data"}), 500

    return jsonify(results)

# TODO: Broken query
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
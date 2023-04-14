from flask import Flask, request, jsonify
from api_log import BotLog
import os
from mariadb import Config

app = Flask(__name__)
logger = BotLog('api')
db = Config()

@app.route('/latest')
def get_latest():
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
    logger.info(f'Got API request for latest data from {request.remote_addr}')
    table = request.args.get('table')
    try:
        results = db.get_yesterday(table)
    except Exception as e:
        logger.error(f'Error getting latest data: {e}')
        return jsonify({"error": f"Error getting latest data"}), 500

    return jsonify(results)

@app.route('/lastweek')
def get_last_week():
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
    logger.info(f'Got API request to run query {request.remote_addr}')
    logger.info(f'Query: {request.args.get("query")}')
    api_key = request.args.get('api_key')
    sql_query = request.args.get('query')

    if api_key != os.environ.get('API_KEY'):
        logger.error(f'Invalid API key from {request.remote_addr}')
        logger.error(f'Given API key: {api_key}')
        logger.error(f'Given query: {sql_query}')
        return jsonify({"error": "Invalid API Key"}), 401

    try:
        results = db.run_query(sql_query)
    except Exception as e:
        logger.error(f'Error running query: {e}')
        return jsonify({"error": f"Error running query"}), 500

    logger.info(f'Found {len(results)} results')
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

import os
import requests
from urllib.parse import urlencode
from completion_log import BotLog
from flask import Flask, request, jsonify
app = Flask(__name__)

API_KEY = os.environ.get('API_KEY')
PARKING_API_URL = os.environ.get('PARKING_API_URL')
logger = BotLog('completion-manager')



def call_query_endpoint(sql_query):
    if not validate_sql_query(sql_query):
        logger.error("Malicious SQL query detected, aborting.")
        return None

    try:
        params = urlencode({'api_key': API_KEY, 'query': sql_query})
        url = f"{PARKING_API_URL}/query?{params}"
        response = requests.get(url)

        if response.status_code != 200:
            logger.error(f"API returned a non-200 status code: {response.status_code}")
            return None

        return response.json()
    except Exception as e:
        logger.error(f"Error calling API endpoint: {e}")
        return None
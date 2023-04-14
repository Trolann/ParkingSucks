from templates import *
from os import getenv
from langchain.chat_models import ChatOpenAI
from langchain.chains import OpenAIModerationChain
from completion_log import BotLog
from flask import Flask, request, jsonify, make_response
import requests
import json
import os

app = Flask(__name__)

from dotenv import load_dotenv
load_dotenv('completion_manager.env')

logger = BotLog('completion-manager')
chat = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7
    )

def complete_moderation_chain(query: str) -> bool:
    try:
        moderation_chain = OpenAIModerationChain(error=True)
        moderation_chain.run(query)
        logger.info('Moderation chain passed')
        return True
    except ValueError as e:
        logger.error(f"Flagged content detected: {e}")
        logger.error(f"Query: {query}")
        return False

def is_this_ok(query) -> bool:
    response = chat(query.to_messages()).content
    logger.info(f'Got response: {response} (query: {query})')
    if '@@@@@@@@' in response:
        logger.critical(f"UNSAFE QUERY DETECTED: {query}")
        return False
    if '!!!!!!!!' in response:
        logger.info(f'Found a safe query')
        return True
    else:
        logger.error(f'Unable to determine safety of query: {query}')
        return False

def get_sql_query(question) -> str:
    logger.info(f'Getting SQL query for question: {question}')
    question = get_sql_gen_prompt(question)
    return chat(question.to_messages()).content


def get_final_answer(question, parking_info) -> str:
    logger.info(f'Getting final answer for question: {question}')
    question = get_final_answer_prompt(question, parking_info)
    return chat(question.to_messages()).content

def call_parking_api(username, message, sql_query):
    payload = {"api_key": getenv("PARKING_API_KEY"), "query": sql_query, "username": username, "message": message}
    url = getenv("PARKING_API_URL") + '/query'
    response = requests.get(url, params=payload)

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        raise Exception(f"Error calling API. Status code: {response.status_code}, response: {response.text}")

@app.route('/completion', methods=['POST'])
def completion():
    api_key = request.form.get('api_key')
    username = request.form.get('username')
    message = request.form.get('message')
    logger.info(f'Got request from {username} with message: {message}')

    if api_key != os.getenv('API_KEY'):
        logger.error(f'Invalid API key: {api_key} from {request.remote_addr}/{username}')
        return jsonify({'error': 'Invalid API key'}), 401

    #is_ok = is_this_ok(get_safety_prompt(message))

    #if not is_ok:
    #    logger.info(f'Query not allowed: {message} (username: {username})')
    #    return jsonify({'error': 'Query not allowed'}), 400

    sql_query = get_sql_query(message)
    logger.info(f'Got SQL query from OpenAI: {sql_query}')

    parking_info = call_parking_api(username, message, sql_query)
    logger.info(f'Called parking API: {parking_info}')
    final_answer = get_final_answer(message, parking_info)
    logger.info(f'Got final answer: {final_answer}')

    return make_response(jsonify(final_answer), 200, {'Content-Type': 'application/json'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

from completion_manager.parking_info import get_sql_query, call_parking_api
from utils import get_prompt, archive_completion
from os import getenv
from langchain.chat_models import ChatOpenAI
from langchain.chains import OpenAIModerationChain
from completion_log import BotLog
from flask import Flask, request, jsonify, make_response
import os

app = Flask(__name__)

from dotenv import load_dotenv
load_dotenv('completion_manager.env')

logger = BotLog('completion-manager')
chat = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7
    )
chat4 = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7,
    )
chat4.model_name = "gpt-4"

def complete_moderation(query: str) -> bool:
    '''
    This is required by OpenAI to use their model in any production capacity. It's free.
    :param query:
    :return:
    '''
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
    '''
    Have the LLM determine if the query is associated with parking, classes or similar.
    Specifically reject anything which is asking to do harm or alter the table.
    Templates: ok_system.txt and ok_human.txt
    :param query:
    :return:
    '''
    response = chat(query.to_messages()).content
    archive_completion(query.to_messages(), response)
    logger.info(f'Got response: {response} (query: {query})')
    if '!!!!!!!!' in response:
        logger.info(f'Found a safe query')
        return True
    # The nuance here is important for logging/debugging, but either way we're not doing it
    if '@@@@@@@@' in response:
        logger.critical(f"UNSAFE QUERY DETECTED: {query}")
    else:
        logger.error(f'Unable to determine safety of query: {query}')
    return False

def get_final_answer(question, parking_info) -> str:
    '''
    Takes given parking information and generates the final user answer. This is also the final safety check.
    :param question:
    :param parking_info:
    :return:
    '''
    logger.info(f'Getting final answer for question: {question}')
    question = get_prompt(question, 'final', results=parking_info)

    # Get the final response
    response = chat(question.to_messages()).content
    #response = chat4(question.to_messages()).content

    archive_completion(question.to_messages(), response)
    return response

# TODO: Breakout to api.py
# TODO: Implement async api calls
@app.route('/completion', methods=['POST'])
def completion():
    '''
    The completion endpoint. Gets a message and generates the executes the chain.
    Returns to the user the message which should be shown in the UI
    :return:
    '''
    api_key = request.form.get('api_key')
    username = request.form.get('username')
    message = request.form.get('message')
    logger.info(f'Got request from {username} with message: {message}')

    if api_key != os.getenv('API_KEY'):
        logger.error(f'Invalid API key: {api_key} from {request.remote_addr}/{username}')
        return jsonify({'error': 'Invalid API key'}), 401

    is_ok = is_this_ok(get_prompt(message, 'ok'))

    if not is_ok:
        logger.info(f'Query not allowed: {message} (username: {username})')
        return jsonify({'error': 'Query not allowed'}), 400

    sql_query = get_sql_query(message)
    logger.info(f'Got SQL query from OpenAI: {sql_query}')
    parking_info = call_parking_api(username, message, sql_query)

    if len(parking_info) < 5:
        logger.error(f'Parking API returned too little data: {parking_info}')
        try_again = f"This query didn't quite work:\n {sql_query}.\nHere was the original request:\n{message}\nPlease try again."
        sql_query = get_sql_query(try_again, gpt4=True)
        logger.info(f'Got a new SQL query from OpenAI: {sql_query}')
        parking_info = call_parking_api(username, message, sql_query)
        parking_info = "I couldn't get any parking information. Tell the user to try and ask in a different way." if len(parking_info) < 5 else parking_info
    logger.info(f'Called parking API: {parking_info}')

    final_answer = get_final_answer(message, parking_info)
    logger.info(f'Got final answer: {final_answer}')

    # TODO: REMOVE PRINTING SQL QUERY TO DISCORD
    # Just delete this whole thing, final_answer is perfect above
    # final_answer = f"Final Answer:\n {final_answer}" + f"\nSQL:\n ```\n {sql_query} \n```"

    return make_response(jsonify(final_answer), 200, {'Content-Type': 'application/json'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

# Prompt 1:
# Add a flask api to this application. There should be 1 end-point: /completion
# which confirms the API_KEY environment variable matches the api_key argument.
# The 'query' argument should be passed to the 'is_this_ok' function and if it's ok,
# then to the 'get_sql_query' function. The /completion endpoint should return
# the result of get_sql_query.

# Prompt 2:
# Write python function(s) to call this api with the required parameters and
# decode the response. Update the parking-api.py file as needed.

# Prompt 3:
# <Gave Code>
# <Gave errors>
# <Gave API endpoint code>
# How can I properly decode final_answer in the discord bot to display it in the chat room?

# Prompt 4:
# This function:
# <gave get_sql_query>
# Is taking this response value:
# <Gave example response>
# and not properly returning the extracted SQL query. Fix it, please.

# Prompt 5:
# Take this query and use the CONCAT or similar function to add a single row to the top that says:
# Data generated for Tuesday and Thursday's from 12:30pm until 1:30pm.
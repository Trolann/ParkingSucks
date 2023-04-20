import os
from flask import request, jsonify, make_response
from answer_chains import app, is_this_ok, get_final_answer
from sql_chains import get_sql_query, call_parking_api
from utils import get_prompt
from completion_log import BotLog

logger = BotLog('completion-api')

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

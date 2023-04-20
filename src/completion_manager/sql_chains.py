import json
from os import getenv
from re import sub
from completion_log import BotLog
from langchain.chat_models import ChatOpenAI

import requests

from utils import get_prompt, archive_completion

logger = BotLog('sql-chains')
chat = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7
    )
chat4 = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7,
    )
chat4.model_name = "gpt-4"

def get_sql_query(question, gpt4=False) -> str:
    '''
    Sends requests to the model to get a runnable SQL query. Takes the response and finds the query
    and extracts it, checks its validity and returns it.
    :param question:
    :param gpt4:
    :return:
    '''
    query = None
    logger.info(f'Getting SQL query for question: {question}')

    # Get the messages to send to the model
    question = get_prompt(question, 'sql')

    # Choose the model, gpt4 is slow af, but never misses
    if not gpt4:
        response = chat(question.to_messages()).content
    else:
        response = chat4(question.to_messages()).content

    logger.info(f'Got response: \n{response}\n')

    # We likely always need to extract the query
    if not response.startswith('SELECT'):
        query_start = response.find("!!!!!!!!")
        if query_start == -1:
            logger.error(f'Unable to find query in response: {response}')
            return ''
        query_start += len("!!!!!!!!")
        query_end = len(response)

        # First pull out the query part
        query = response[query_start:query_end]

        # Remove any markdown
        query = sub(r'```[a-zA-Z]*', '```', query)

        # Reduce tokens
        return_val = query.replace("\n", " ")
        logger.info(f'Extracted query: \n{return_val}\n')
    else:
        return_val = response

    archive_completion(question.to_messages(), response)

    # Basic text string checks
    if not validate_sql_query(return_val):
        logger.error(f'Invalid SQL query: {return_val}')
        return ''
    return return_val


def call_parking_api(username, message, sql_query):
    '''
    Calls the parking api with the given SQL query
    :param username:
    :param message:
    :param sql_query:
    :return:
    '''
    payload = {
        "api_key": getenv("PARKING_API_KEY"),
        "query": sql_query,
        "username": username, # Not implemented, for future
        "message": message}
    url = getenv("PARKING_API_URL") + '/query'
    response = requests.get(url, params=payload)

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        raise Exception(f"Error calling API. Status code: {response.status_code}, response: {response.text}")

def validate_sql_query(sql_query):
    '''
    Simple string check to ensure no malicious commands are being executed.
    :param sql_query:
    :return:
    '''
    malicious_keywords = ['DROP', 'ALTER', 'CREATE', 'UPDATE',
                          'DELETE', 'INSERT', 'GRANT', 'REVOKE',
                          'TRUNCATE', 'RENAME', 'EXEC', 'MERGE',
                          'SAVEPOINT', 'ROLLBACK', 'COMMIT']
    for keyword in malicious_keywords:
        if keyword.lower() in sql_query.lower():
            logger.error(f"Malicious keyword '{keyword}' found in SQL query: {sql_query}")
            return False
    return True
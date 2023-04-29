import json
from os import getenv, environ
import re
from datetime import datetime
from completion_log import BotLog
from utils import get_prompt, archive_completion, make_pretty
from langchain.chat_models import ChatOpenAI
import requests
import re
import newrelic.agent
import aiohttp
import traceback
from nr_openai_observability import monitor

#monitor.initialization(getenv('NEW_RELIC_LICENSE_KEY_AI'))
logger = BotLog('sql-paring-chains')
chat = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7
    )

@newrelic.agent.background_task()
async def parking_chain(question, schedule=None, gpt4=False) -> str:
    try:

        commands = await get_commands(question, schedule=schedule, gpt4=gpt4)
        logger.info(f'Got commands: {commands}')
        commands_list = extract_commands(commands)
        logger.info(f'Extracted commands {commands_list}.')

        output = await execute_commands(commands_list, schedule=schedule, gpt4=gpt4)
        logger.info(f'Got parking data: {type(output[0])}')

        try:
            pretty = await make_pretty(output)
            logger.info(f'Got  pretty output.')
        except Exception as e:
            pretty = output
            logger.error(f'Unable to make pretty output: {pretty}')
            # print full traceback to console gracefully
            raise e
        return pretty
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.error(f'Error in parking chain: {traceback_str}')
        return 'There was an error in the parking chain'

@newrelic.agent.background_task()
async def get_commands(question, schedule, gpt4=False, table='sjsu') -> str:
    logger.info(f'Getting commands query for question: {question}')
    if gpt4:
        logger.info('Using GPT4 command generation')

    if not schedule:
        schedule = 'This is the user\'s first time using the system and we have no schedule for them.'
    question = await get_prompt(question, 'commands', table=table, schedule=schedule)

    chat.model_name = "gpt-3.5-turbo" if not gpt4 else "gpt-4"

    command_response = chat(question.to_messages())
    command_text = command_response.content

    await archive_completion(question.to_messages(), command_text)
    logger.info(f'Got list of commands.')

    return command_text

@newrelic.agent.background_task()
async def execute_commands(commands_list, schedule=None, gpt4=False) -> list:
    output = []

    for command in commands_list:
        logger.info(f'Executing command: {command}')
        api_params = {}

        try:
            if command["command"] == "run_query":
                if not validate_sql_query(command["query"]):
                    logger.error(f'Invalid SQL query: {command["query"]}')
                    return ['There was an unsafe request made and we could not complete it']
                api_params["endpoint"] = "run_query"
                try:
                    api_params["sql_query"] = await generate_sql_query(command["query"], schedule=schedule, gpt4=gpt4)
                except Exception as e:
                    traceback_str = traceback.format_exc()
                    logger.error(f'Command: {command}')
                    logger.error(f'Error generating SQL query: {traceback_str}')
                    logger.error(f'API params: {api_params}')

                    return ['There was an error generating the SQL query']
            else:
                api_params["endpoint"] = command["command"]
                api_params["table"] = command["table"]

                if command["command"] == "average":
                    api_params["day"] = command["day"]
                    api_params["time"] = command["time"]

            response = await call_parking_api(**api_params)
            output.append(response)
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.error(f'Error executing command: {command}, {e}')
            logger.debug(f'Traceback for {command}: {traceback_str}')
            return ['There was an error executing the command']

    return output

@newrelic.agent.background_task()
async def call_parking_api(endpoint, table=None, day=None, time=None, sql_query=None) -> list:
    if sql_query and endpoint != 'query':
        logger.error(f"Invalid endpoint: {endpoint} for query: {sql_query}")
        return list('')
    payload = {
        "api_key": getenv("PARKING_API_KEY"),
        "endpoint": endpoint
    }

    try:
        if sql_query:
            payload["query"] = cleanup_query(sql_query)
        elif table:
            payload["table"] = table

        if day and time:
            payload["day"] = day
            payload["time"] = time
        elif day or time:
            logger.error(f"Invalid day or time: {day}, {time}")
            return list('')

        url = f"{getenv('PARKING_API_URL')}/{endpoint}"
        async with aiohttp.ClientSession() as session:
            parking_info = "I couldn't get any parking information. Tell the user to try and ask in a different way."
            async with session.get(url, params=payload) as response:
                if response.status == 200:
                    parking_info = json.loads(await response.text())
                    if sql_query and len(parking_info) < 5:
                        logger.error(f'Parking API returned too little data: {parking_info}')
                    logger.info(f'Called parking API: {parking_info}')

                    return list(parking_info)
                else:
                    traceback_str = traceback.format_exc()
                    logger.error(f'Error calling parking API (top): {e}')
                    logger.debug(f'Traceback for parking API: {traceback_str}')
                    raise Exception(f"Error calling API. Status code: {response.status}, response: {parking_info}")
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.error(f'Error calling parking API: {e}')
        logger.debug(f'Traceback for parking API: {traceback_str}')
        return list('')


@newrelic.agent.background_task()
async def generate_sql_query(question, schedule, gpt4=False) -> str:
    logger.info(f'Generating a SQL query')

    # Get the messages to send to the model
    question = await get_prompt(question, 'sql', table='sjsu', schedule=schedule)

    # Choose the model, gpt4 is slow af, but never misses
    chat.model_name = "gpt-3.5-turbo" if not gpt4 else "gpt-4"
    sql_response = chat(question.to_messages())
    sql_text = sql_response.content

    await archive_completion(question.to_messages(), sql_text)

    logger.info(f'Got SQL query')

    if not validate_sql_query(sql_text):
        logger.error(f'Invalid SQL query: {sql_text}')
        return 'There was an unsafe request made and we could not complete it'

    # Basic text string checks
    return sql_text

@newrelic.agent.background_task()
def extract_commands(text):
    command_patterns = {
        "latest": r"!!!!!!!!,(\w+)",
        "yesterday": r"@@@@@@@@,(\w+)",
        "lastweek": r"########,(\w+)",
        "average": r"\*\*\*\*\*\*\*\*,(\w+),(\w+),(\d{2}:\d{2}:\d{2})",
        "run_query": r"&&&&&&&&,(.+)"
    }

    extracted_commands = []
    commands_count = {"run_query": 0}

    try:
        for command, pattern in command_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                if command == "average":
                    table_name, day, time = match.group(1), match.group(2), match.group(3)
                    logger.info(f'Old day {day}')
                    day = adjust_day(day)
                    logger.info(f'Got day {day}')
                    time = adjust_time(time)
                    extracted_commands.append({"command": command, "table": table_name, "day": day, "time": time})
                elif command == "run_query":
                    query = match.group(1)
                    extracted_commands.append({"command": command, "query": query})
                    commands_count["run_query"] += 1
                else:
                    table_name = match.group(1)
                    extracted_commands.append({"command": command, "table": table_name})
    except Exception as e:
        logger.error(f'Error extracting commands: {e}')
        return ["Unable to get parking information asdf"]

    if len(extracted_commands) <= 4 and commands_count["run_query"] <= 1:
        return extracted_commands
    else:
        return ["Unable to get parking information"]

@newrelic.agent.background_task()
def cleanup_query(sql_query):
    if not sql_query.startswith('SELECT'):
        query_start = sql_query.find("!!!!!!!!")
        if query_start == -1:
            logger.error(f'Unable to find query in response: {sql_query}')
            return ''
        query_start += len("!!!!!!!!")
        query_end = len(sql_query)

        query = sql_query[query_start:query_end]

        query = re.sub(r'```[a-zA-Z]*', '```', query)

        return_val = query.replace("\n", " ")
        logger.info(f'Extracted query: \n{return_val}\n')
        return return_val
    return sql_query

@newrelic.agent.background_task()
def validate_sql_query(sql_query):
    malicious_keywords = ['DROP', 'ALTER', 'CREATE', 'UPDATE',
                          'DELETE', 'INSERT', 'GRANT', 'REVOKE',
                          'TRUNCATE', 'RENAME', 'EXEC', 'MERGE',
                          'SAVEPOINT', 'ROLLBACK', 'COMMIT']

    for keyword in malicious_keywords:
        if keyword.lower() in sql_query.lower():
            logger.error(f"Malicious keyword '{keyword}' found in SQL query: {sql_query}")
            return False

    return True

@newrelic.agent.background_task()
def adjust_day(day):
    day_mapping = {
        'M': 'Monday',
        'T': 'Tuesday',
        'W': 'Wednesday',
        'R': 'Thursday',
        'F': 'Friday',
        'Sa': 'Saturday',
        'Su': 'Sunday',
        'Mon': 'Monday',
        'Tues': 'Tuesday',
        'Tue': 'Tuesday',
        'Wed': 'Wednesday',
        'Thurs': 'Thursday',
        'Thu': 'Thursday',
        'Fri': 'Friday',
        'Sat': 'Saturday',
        'Sun': 'Sunday',
        'Monday': 'Monday',
        'Tuesday': 'Tuesday',
        'Wednesday': 'Wednesday',
        'Thursday': 'Thursday',
        'Friday': 'Friday',
        'Saturday': 'Saturday',
        'Sunday': 'Sunday',
        'monday': 'Monday',
        'tuesday': 'Tuesday',
        'wednesday': 'Wednesday',
        'thursday': 'Thursday',
        'friday': 'Friday',
        'saturday': 'Saturday',
        'sunday': 'Sunday'
    }

    day = day.strip()
    day_lower = day.lower()

    if day_lower in day_mapping.values():
        return day
    elif day in day_mapping:
        return day_mapping[day]
    else:
        for key, value in day_mapping.items():
            if value.lower().startswith(day_lower):
                return value
        return "Invalid day"

@newrelic.agent.background_task()
def adjust_time(time):
    logger.info(f'Adjusting time: {time}')
    try:
        return datetime.strptime(time, "%H:%M:%S").strftime("%H:%M:%S")
    except ValueError:
        return "Invalid time"

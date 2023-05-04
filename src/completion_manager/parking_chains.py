import json
from os import getenv
from datetime import datetime
from completion_log import BotLog
from utils import get_prompt, archive_completion, make_pretty
from langchain.chat_models import ChatOpenAI
import re
import newrelic.agent
import aiohttp
import traceback

logger = BotLog('sql-paring-chains')
chat = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7
    )

@newrelic.agent.background_task()
async def parking_chain(question, schedule=None, gpt4=False) -> str:
    """
    The parking chain gets a list of commands to run against the parking API, executes them
    including any custom SQL queries, and then cleans them to return them to the LLM.
    :param question:
    :param schedule:
    :param gpt4:
    :return:
    """
    logger.info(f'Starting parking chain for question: {question}')
    try:
        # Get commands, extract them and execute them
        commands = await get_commands(question, schedule=schedule, gpt4=gpt4)
        logger.debug(f'Got commands: {commands}')
        commands_list = extract_commands(commands)
        logger.debug(f'Extracted commands {commands_list}.')
        # Call the Parking API
        output = await execute_commands(commands_list)
        logger.debug(f'Got parking data: {output[0]}')

        # Cleanup the response into a table
        try:
            pretty = await make_pretty(output)
            logger.debug(f'Got  pretty output.')
        except Exception as e:
            # Already formatted (single string), return it
            pretty = output
            logger.error(f'Unable to make pretty output: {e}\n{pretty}')

        return pretty
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.critical(f'Error in parking chain: {traceback_str}')
        return 'Parking information is not available right now.'

@newrelic.agent.background_task()
async def get_commands(question, schedule, gpt4=False, table='sjsu') -> str:
    """
    Queries the GPT endpoint to get a list of commands to be extracted.
    :param question:
    :param schedule:
    :param gpt4:
    :param table:
    :return:
    """
    logger.debug(f'Getting commands query for question: {question}')
    if gpt4:
        logger.debug('Using GPT4 command generation')

    # For memory in the future
    if not schedule:
        schedule = 'This is the user\'s first time using the system and we have no schedule for them.'
    question = await get_prompt(question, 'commands', schedule=schedule)

    # Get the commands
    chat.model_name = "gpt-3.5-turbo"# if not gpt4 else "gpt-4"
    command_response = chat(question.to_messages())
    command_text = command_response.content
    logger.debug(f'Got command response: {command_text}')

    await archive_completion(question.to_messages(), command_text)
    logger.info(f'Got list of commands: {command_text}')

    return command_text

@newrelic.agent.background_task()
def extract_commands(text):
    # Likely for questions like 'Where can I charge my car?'
    if "It is all good" in text:
        logger.debug(f'No commands to extract in text: {text}')
        return []

    command_patterns = {
        "latest": r"Get latest parking information: (True|False)",
        "average": r"Get average parking information for day of the week: (True|False)",
        "days": r"Day\(s\) of the week: ([\w,]+|None)",
        "time": r"Time of the day: (\d{2}:\d{2}:\d{2}|None)"
    }

    extracted_commands = {}

    try:
        for command, pattern in command_patterns.items():
            logger.debug(f'Extracting command: {command} with pattern: {pattern}')
            match = re.search(pattern, text)
            if match:
                logger.info(f'Extracted command: {command} with value: {match.group(1)}')
                extracted_commands[command] = match.group(1)
    except Exception as e:
        logger.error(f'Error extracting commands: {e}')
        return []

    return extracted_commands


@newrelic.agent.background_task()
async def execute_commands(commands):
    if not commands:
        logger.debug('No commands to execute.')
        return 'It is all good'

    output = []

    # Individual try/catch because the model may only screw up one extraction
    try:
        if commands.get("latest") == "True":
            logger.info(f'Calling parking API for latest data.')
            response = await call_parking_api(endpoint="latest")
            logger.debug(f'Got response from parking API: {response}')
            output.append(response)
    except Exception as e:
        logger.error(f'Error executing get_latest from command executor: {e}')
        return 'There was an error getting the latest data.'

    # Likely called every time, multiple times
    try:
        if commands.get("average") == "True":
            logger.info(f'Calling parking API for average data.')
            days = commands.get("days")
            days_list = [adjust_day(day) for day in days.split(',')] if days != "None" else None
            time = commands.get("time")
            adjusted_time = adjust_time(time) if time != "None" else None
            if not days_list or not adjusted_time:
                logger.error(f'Error getting average data for days: {days} and time: {time} from command executor.')
                return 'There was an error executing the command'
            for day in days_list:
                response = await call_parking_api(endpoint="average", day=day, time=adjusted_time)
                logger.debug(f'Got response from parking API: {response}')
                output.append(response)
    except Exception as e:
        days = commands.get("days")
        time = commands.get("time")
        logger.critical(f'Error getting average data for days: {days} and time: {time} from command executor: {e}')
        return 'There was an error executing the command'

    return output


@newrelic.agent.background_task()
async def call_parking_api(endpoint=None, table='sjsu', day=None, time=None) -> list:
    payload = {
        "api_key": getenv("PARKING_API_KEY"),
        "endpoint": endpoint,
        "table": table
    }
    # Make sure it's valid to get the average
    if day and time:
        payload["day"] = day
        payload["time"] = time
    elif day or time: # Only here if not and
        logger.error(f"Invalid day or time: {day}, {time}")
        return list('')

    try:
        url = f"{getenv('PARKING_API_URL')}/{endpoint}"
        async with aiohttp.ClientSession() as session:
            parking_info = "I couldn't get any parking information. Tell the user to try and ask in a different way."
            async with session.get(url, params=payload) as response:
                logger.debug(f'Called parking API endpoint: {endpoint}')
                if response.status == 200:
                    parking_info = json.loads(await response.text())
                    logger.info(f'Called parking API successfully.')
                    logger.debug(f'Got response from parking API: {parking_info}')
                    return list(parking_info)
                else:
                    traceback_str = traceback.format_exc()
                    logger.critical(f'Error calling parking API (top): {e}')
                    logger.debug(f'Traceback for parking API: {traceback_str}')
                    raise Exception(f"Error calling API. Status code: {response.status}, response: {parking_info}")
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.critical(f'Error calling parking API: {e}')
        logger.debug(f'Traceback for parking API: {traceback_str}')
        return list('')
@newrelic.agent.background_task()
def adjust_day(day):
    """
    Adjusts the day to the correct format for the API
    :param day:
    :return:
    """
    logger.debug(f'Adjusting day: {day}')
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
        logger.error(f"Invalid day: {day}")
        return "Invalid day"

@newrelic.agent.background_task()
def adjust_time(time):
    """
    Adjusts the time to the correct format for the API
    :param time:
    :return:
    """
    logger.debug(f'Adjusting time: {time}')
    try:
        return datetime.strptime(time, "%H:%M:%S").strftime("%H:%M:%S")
    except ValueError:
        return "Invalid time"

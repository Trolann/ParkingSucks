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

    try:
        # Get commands, extract them and execute them
        commands = await get_commands(question, schedule=schedule, gpt4=gpt4)
        logger.info(f'Got commands: {commands}')
        commands_list = extract_commands(commands)
        logger.info(f'Extracted commands {commands_list}.')
        output = await execute_commands(commands_list)
        logger.info(f'Got parking data: {type(output[0])}')

        # Cleanup the response
        try:
            pretty = await make_pretty(output)
            logger.info(f'Got  pretty output.')
        except Exception as e:
            # Already formatted (single string), return it
            pretty = output
            logger.error(f'Unable to make pretty output: {e}\n{pretty}')

        return pretty
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.error(f'Error in parking chain: {traceback_str}')
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
    logger.info(f'Getting commands query for question: {question}')
    if gpt4:
        logger.info('Using GPT4 command generation')

    # For memory in the future
    if not schedule:
        schedule = 'This is the user\'s first time using the system and we have no schedule for them.'
    question = await get_prompt(question, 'commands', schedule=schedule)

    # Get the commands
    chat.model_name = "gpt-3.5-turbo"# if not gpt4 else "gpt-4"
    command_response = chat(question.to_messages())
    command_text = command_response.content

    await archive_completion(question.to_messages(), command_text)
    logger.info(f'Got list of commands.')

    return command_text

@newrelic.agent.background_task()
def extract_commands(text):
    if "It is all good" in text:
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
            logger.info(f'Extracting command: {command} with pattern: {pattern}')
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
        return 'It is all good'

    output = []

    try:
        if commands.get("latest") == "True":
            response = await call_parking_api(endpoint="latest")
            output.append(response)
    except Exception as e:
        logger.error(f'Error executing get_latest from command executor: {e}')
        return 'There was an error getting the latest data.'

    try:
        if commands.get("average") == "True":
            days = commands.get("days")
            days_list = [adjust_day(day) for day in days.split(',')] if days != "None" else None
            time = commands.get("time")
            adjusted_time = adjust_time(time) if time != "None" else None

            for day in days_list:
                response = await call_parking_api(endpoint="average", day=day, time=adjusted_time)
                output.append(response)
    except Exception as e:
        days = commands.get("days")
        time = commands.get("time")
        logger.error(f'Error getting average data for days: {days} and time: {time} from command executor: {e}')
        return 'There was an error executing the command'

    return output


@newrelic.agent.background_task()
async def call_parking_api(endpoint=None, table='sjsu', day=None, time=None) -> list:
    payload = {
        "api_key": getenv("PARKING_API_KEY"),
        "endpoint": endpoint
    }

    try:
        if table:
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

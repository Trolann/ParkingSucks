from os import getenv
import re
import aiohttp
import newrelic.agent
from discord_log import BotLog

logger = BotLog('discord-bot-utils')

@newrelic.agent.background_task()
def make_pretty(query_results):
    # Determine the maximum length for each column
    column_widths = {}
    data_line = ''
    for entry in query_results:
        print(f'entry: {entry}')
        for key, value in entry.items():
            if key == 'address':
                continue
            if key not in column_widths and 'Data above' not in str(value):
                column_widths[key] = len(str(key))
            if 'Data above' in str(value):
                data_line = str(value)
                continue
            column_widths[key] = max(column_widths[key], len(str(value)))

    # Create the header row
    header = '| ' + ' | '.join([f"{key:<{column_widths[key]}}" for key in column_widths]) + ' |'
    separator = '+-' + '-+-'.join(['-' * column_widths[key] for key in column_widths]) + '-+'

    # Create the table rows
    rows = []
    for i, entry in enumerate(query_results):
        # Check if this is the last row
        if i == len(query_results) - 1:
            # Append just the value of the last column
            row = '\n' + data_line
        else:
            # Append the full row
            try:
                row = '| ' + ' | '.join([f"{entry[key]:<{column_widths[key]}}" for key in column_widths]) + ' |'
            except Exception as e:
                pass
        rows.append(row)

    # Combine the header, separator, and rows
    table = '\n'.join([header, separator] + rows)
    return '```\n' + table + '\n```'

@newrelic.agent.background_task()
async def call_completion_api(username, message, channel, message_id):
    '''
    Call the completion API to get the messages
    :param username:
    :param message:
    :return:
    '''
    async with aiohttp.ClientSession() as session:
        url = getenv("COMPLETION_API_URL") + '/completion'
        api_key = getenv("COMPLETION_API_KEY")
        try:
            print('trying')
            response = await fetch(session, url, api_key, username, message, channel, message_id)
        except Exception as e:
            logger.error(f"Error calling completion API: {e}")
            return {'error': 'Error calling completion API'}
        return response

@newrelic.agent.background_task()
async def call_parking_api(username, endpoint, params=None, sql_query=None):
    '''
    Call the parking API to get the data
    :param username:
    :param message:
    :param sql_query:
    :param endpoint:
    :return:
    '''
    async with aiohttp.ClientSession() as session:
        url = f"{getenv('PARKING_API_URL')}/{endpoint}"
        payload = {
            "api_key": getenv("PARKING_API_KEY"),
            "username": username,
        }
        if params:
            for p in params:
                payload[p] = params[p]
        if sql_query:
            payload['sql_query'] = sql_query
        try:
            response = await session.get(url, params=payload)
        except Exception as e:
            raise Exception(f"Error calling parking API: {e}")
        if response.status == 200:
            return make_pretty(await response.json())
        else:
            raise Exception(f"Error calling API. Status code: {response.status}, response: {response.text}")


async def fetch(session, url, api_key, username, message, channel, message_id=0):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'api_key': api_key, 'username': username, 'message': message, 'channel': channel}
    if message_id > 0:
        data['message_id'] = message_id
    print('fetching')
    async with session.post(url, headers=headers, data=data) as response:
        return await response.json(content_type=None)

@newrelic.agent.background_task()
def convert_schedule(input_string):
    lines = input_string.strip().split('\n')
    formatted_output = []
    class_name, days_times, location = None, None, None

    for line in lines:
        if line.startswith("Class"):
            continue

        # Check for class name pattern
        if not class_name and re.match(r'[A-Z]+ \d+[A-Z]*-\d+[A-Z]*', line.strip()):
            class_name = line.strip()
        elif "AM" in line or "PM" in line:
            days_times = line.strip()
        elif "Building" in line or "Line" in line or "TBA" in line or "Boccardo" in line:
            location = line.strip()

        if class_name and days_times and location:
            formatted_output.append(f"{class_name}: {days_times}, {location}")
            class_name, days_times, location = None, None, None

    return '\n'.join(formatted_output)


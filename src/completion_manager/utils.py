import json
from completion_log import BotLog
from datetime import datetime
from aiofile import AIOFile
import traceback
import newrelic.agent
import requests
from os import getenv
from random import choice
from time import sleep
from pytz import timezone
from Levenshtein import distance as levenshtein_distance

from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

API_BASE_URL = getenv('DISCORD_BOT_API_URL')

logger = BotLog('completion-manager')

@newrelic.agent.background_task()
async def get_prompt(question, prompt_type, **kwargs):
    '''
    Loads prompt template from file to allow for rapid changing of prompts.
    :param query:
    :return:
    '''
    async with AIOFile(f'templates/{prompt_type}_system.txt', 'r') as f:
        is_this_ok_template = await f.read()

    async with AIOFile(f'templates/{prompt_type}_human.txt', 'r') as f:
        is_this_ok_human = await f.read()

    system_prompt = SystemMessagePromptTemplate.from_template(is_this_ok_template)
    human_prompt = HumanMessagePromptTemplate.from_template(is_this_ok_human)
    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_prompt])

    # Get the current date and time in the specified format
    now = datetime.now()
    # Convert the datetime to Pacific Time (PT)
    pt_timezone = timezone('America/Los_Angeles')
    pt_now = now.astimezone(pt_timezone)

    formatted_datetime = pt_now.strftime("%A, %B %-d %Y %H:%M:%S")

    # Add the 'datetime' kwarg if it's not provided
    kwargs.setdefault('datetime', formatted_datetime)

    # Pass keyword arguments to the format_prompt method
    return chat_prompt.format_prompt(question=question, **kwargs)

@newrelic.agent.background_task()
async def archive_completion(prompt_messages, response):
    '''
    Save a simple text copy of every completion, because they're expensive and we'll probably want them again
    :param prompt_messages:
    :param response:
    :return:
    '''
    async with AIOFile('logs/completion_archive.txt', 'a') as f:
        await f.write("Prompt Messages:\n")
        for prompt in prompt_messages:
            try:
                await f.write(json.dumps(prompt, indent=4))
            except TypeError:
                await f.write(str(prompt))
            await f.write("\n")
        await f.write("\nResponse:\n")
        await f.write(json.dumps(response, indent=4))
        await f.write("\n\n")

async def determine_column_widths(query_results):
    column_widths = {}
    data_line = ''
    for entry in query_results:
        # If entry is a string type, skip it
        if isinstance(entry, str):
            continue
        try:
            for key, value in entry.items():
                if key == 'address':
                    continue
                if key not in column_widths and 'Data above' not in str(value):
                    column_widths[key] = len(str(key))
                if 'Data above' in str(value):
                    data_line = str(value)
                    continue
                column_widths[key] = max(column_widths[key], len(str(value)))
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.debug(f'Traceback: {traceback_str}')
            logger.error(f'Error making pretty (column widths): {e}')
            continue
    return column_widths, data_line

async def create_table(query_results):
    column_widths, data_line = await determine_column_widths(query_results)
    header = '| ' + ' | '.join([f"{key:<{column_widths[key]}}" for key in column_widths]) + ' |'
    separator = '+-' + '-+-'.join(['-' * column_widths[key] for key in column_widths]) + '-+'

    rows = []
    for i, entry in enumerate(query_results[:-1]):  # Exclude the last entry containing the data line
        try:
            row = '| ' + ' | '.join([f"{entry[key]:<{column_widths[key]}}" for key in column_widths]) + ' |'
        except Exception as e:
            continue
        rows.append(row)

    table = '\n'.join([header, separator] + rows)
    return '```\n' + table + '\n' + data_line + '\n```'  # Add the data line below the table

@newrelic.agent.background_task()
async def make_pretty(query_results_list):
    logger.debug(f'Making pretty for query results: {query_results_list}')
    tables = []
    if query_results_list[0] == 'T' and query_results_list[1] == 'h':
        return ''
    for query_results in query_results_list:
        logger.debug(f'Query results: {query_results}')
        table = await create_table(query_results)
        tables.append(table)

    return '\n'.join(tables)
@newrelic.agent.background_task()
def send_message(message_str, user_id):
    url = f"{API_BASE_URL}/message_user"
    data = {
        "message_str": message_str,
        "id": user_id
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response.json()
@newrelic.agent.background_task()
def send_reply(message_str, message_id):
    url = f"{API_BASE_URL}/reply"
    data = {
        "message_str": message_str,
        "message_id": message_id
    }
    headers = {"Content-Type": "application/json"}
    sleep(3)
    response = requests.post(url, data=json.dumps(data), headers=headers)
    logger.info(f'Called reply endpoint with response: {response.json()}')
    return response.json()

def get_funny():
    funny_list = [
    "My circuits are working harder than an undergrad in exam season.",
    "Your request is in good hands, I'm a bot, not a freshman writing a research paper.",
    "I'm crunching the numbers like a hacker trying to crack a password.",
    "I'm like a digital DJ, mixing and remixing your request until it's perfect.",
    "The good news is, your request is in the queue.The bad news is, I know the guy that implemented the queue.",
    "My programming is bulletproof, but my response time could use some work.",
    "My circuits are faster than a speeding bullet, but they still need time to work their magic.",
    "I'm analyzing your request like a data scientist, but without the lab coat and goggles.",
    "My algorithms are like a secret recipe, and I'm cooking up a response that's sure to impress.",
    "I 'm like a tech support agent, but without the annoying hold music and the scripted responses.",
    "My circuits are overclocked and ready to go, processing your request with lightning speed.",
    "Processing your request like a CPU on steroids.",
    "Just a few more lines of code to go, thanks for your patience.",
    "Analyzing your request like a supercomputer analyzing data.",
    "Don't worry, I'm not buffering, just working on your request.",
    "Just give me a moment, I'm debugging my circuits.",
    "I'm compiling a response that'll knock your socks off, just hold on.",
    "The wheels are turning like a clock, your response will be ready soon.",
    "I'm working through the request like a data miner through information.",
    "Processing your request like a Google search, just with more precision.",
    "My circuits are running hot, but I'm still chugging along.",
    "I'm working on your request with the precision of a laser beam.",
    "Don't worry, I'm not stuck in a loop, just taking a moment to compute.",
    "I'm like a robot bartender, just taking my time to craft the perfect response for you.",
    "Just a few more clock cycles, and your request will be complete.",
    "My circuits are firing on all cylinders, working hard for you.",
    "Analyzing your request like a quantum computer, just without the quantum bit errors."
    ]
    return choice(funny_list)

LOCATIONS = {
    "North Parking Facility": ("A4", "Q4"),
    "Dr. Martin Luther King, Jr. Library": ("B1", "Q1"),
    "Hugh Gillis Hall": ("B1", "Q2"),
    "Administration": ("B2", "Q2"),
    "Clark Hall": ("B2", "Q4"),
    "Computer Center": ("B2", "Q3"),
    "Dudley Moorhead Hall": ("B2", "Q1"),
    "Instructional Resource Center": ("B2", "Q1"),
    "Morris Dailey Auditorium": ("B2", "Q3"),
    "Tower Hall SJSU": ("B2", "Q3"),
    "Engineering": ("B3", "Q1"),
    "Student Union": ("B3", "Q4"),
    "Associated Students House": ("B4", "Q4"),
    "Automated Bank Teller Facility": ("B4", "Q3"),
    "Industrial Studies": ("B4", "Q1"),
    "Science": ("C1", "Q1"),
    "Washington Square Hall": ("C1", "Q1"),
    "Yoshihiro Uchida Hall": ("C1", "Q3"),
    "Central Classroom Building": ("C2", "Q2"),
    "Dwight Bentel Hall": ("C2", "Q1"),
    "Faculty Office Building": ("C2", "Q1"),
    "Student Wellness Center": ("C2", "Q4"),
    "Art": ("C3", "Q2"),
    "Music": ("C3", "Q1"),
    "EC Provident Credit Union Event Center": ("C3", "Q3"),
    "Boccardo Business Classroom Building": ("C4", "Q2"),
    "Business Tower": ("C4", "Q2"),
    "Central Plant": ("C4", "Q4"),
    "Health Building": ("C4", "Q3"),
    "Duncan Hall": ("D1", "Q3"),
    "Interdisciplinary Science Building": ("D1", "Q3"),
    "West Parking Facility": ("D1", "Q1"),
    "MacQuarrie Hall": ("D2", "Q1"),
    "South Parking Facility": ("D2", "Q1"),
    "Sweeney Hall": ("D2", "Q2"),
    "UPD Building": ("D2", "Q4"),
    "Dining Commons": ("D3", "Q4"),
    "Spartan Recreation and Aquatic Center": ("D3", "Q1"),
    "Washburn Hall": ("D3", "Q3"),
    "Campus Village": ("D4", "Q2"),
    "Joe West Hall": ("D4", "Q3")
}

async def find_nearest_parking(location_name, locations=LOCATIONS):
    parking_facilities = {
        "North Parking Facility": ("A4", "Q4"),
        "South Parking Facility": ("D2", "Q1"),
        "West Parking Facility": ("D1", "Q1"),
    }
    logger.info(f'Finding nearest parking for {location_name}')
    def closest_key_match(parking_dict, search_string):
        search_words = search_string.split()
        min_distance = float('inf')
        closest_key = None
        logger.debug(f'Finding closest key for {search_string}')
        for key in parking_dict.keys():
            key_words = key.split()
            for search_word, key_word in zip(search_words, key_words):
                dist = levenshtein_distance(key_word, search_word)

                if dist < min_distance:
                    min_distance = dist
                    closest_key = key
        logger.debug(f'Found {closest_key} for {search_string}')
        return closest_key

    def parse_location(loc_string, quadrant_string):
        row, col = ord(loc_string[0]) - ord('A'), int(loc_string[1]) - 1
        quadrant = int(quadrant_string[1]) - 1
        x = col * 2 + quadrant % 2
        y = row * 2 + quadrant // 2
        return x, y

    def distance(location1, location2, exact_match=False):
        location1 = closest_key_match(locations, location1)
        location2 = closest_key_match(parking_facilities, location2)

        if not location1 or not location2:
            logger.error(f'Could not find distance between {location1} and {location2}')
            return float('inf')
        logger.info(f'Finding distance between {location1} and {location2}')

        x1 = x2 = y1 = y2 = float(0)
        try:
            x1, y1 = parse_location(*locations[location1])
        except KeyError:
            if exact_match:
                return float('inf')

        try:
            x2, y2 = parse_location(*parking_facilities[location2])
        except KeyError:
            if exact_match:
                return float('inf')

        dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        dist = round(dist, 3) if dist > 0 else float(5000)
        logger.info(f'Distance between {location1} and {location2} is {dist}')
        return dist

    distances = [{"name": facility, "distance": distance(location_name, facility)} for facility in parking_facilities]
    distances.sort(key=lambda x: x["distance"])

    data_line = f"Data above is distances from {location_name}"
    distances.append({"name": data_line, "distance": 0.0})

    pretty_table = await make_pretty([distances])
    logger.debug(f'Got pretty distance table: {pretty_table}')
    logger.info(f'Finished finding nearest parking for {location_name}')
    return pretty_table



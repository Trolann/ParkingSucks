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
    formatted_datetime = now.strftime("%A, %B %-d %Y %H:%M:%S")

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
            logger.info(f'Traceback: {traceback_str}')
            logger.info(f'Error: {e}')
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
    tables = []
    for query_results in query_results_list:
        logger.info(f'Query results: {query_results}')
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
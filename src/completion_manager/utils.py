import json
from completion_log import BotLog
from datetime import datetime
from aiofile import AIOFile

from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

logger = BotLog('completion-manager')

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

async def make_pretty(query_results_list):
    tables = []
    for query_results in query_results_list:
        logger.info(f'Query results: {query_results}')
        table = await create_table(query_results)
        tables.append(table)

    return '\n'.join(tables)

import discord
import aiohttp
from os import getenv
from discord_log import BotLog
from discord.ext import commands

# Remove these when you remove call_parking_api
from re import sub

# Replace 'your_bot_token' with your actual bot token
TOKEN = getenv('DISCORD_TOKEN')
logger = BotLog('discord-bot')

# Set up intents to listen for user messages and member join events
intents = discord.Intents.all()
intents.messages = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix='$', intents=intents)

async def call_completion_api(username, message, channel):
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
            response = await fetch(session, url, api_key, username, message, channel)
        except Exception as e:
            logger.error(f"Error calling completion API: {e}")
            return {'error': 'Error calling completion API'}
        return response

# TODO: REMOVE, ONLY NEEDED FOR DEBUG
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


async def fetch(session, url, api_key, username, message, channel):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'api_key': api_key, 'username': username, 'message': message, 'channel': channel}
    async with session.post(url, headers=headers, data=data) as response:
        return await response.json(content_type=None)


@bot.event
async def on_ready():
    logger.info('Bot is ready and connected.')
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    if message.content.lower().startswith('ping?'):
        logger.info(f'Ping? Pong! received from {message.author} in {message.channel}')
        await message.reply('pong!')
        return

    if 'system' in message.channel.name:
        # Extracting endpoint_name and parameters from message.content
        print('system message')
        message_parts = message.content.split()
        endpoint_name = message_parts.pop(0)
        params = {}
        for part in message_parts:
            key, value = part.split('=')
            params[key] = value

        # Calling the modified call_parking_api function
        await message.reply(await call_parking_api(str(message.author), endpoint_name, params=params))
        return

    if bot.user in message.mentions:
        if message.channel.category_id != 1099892029523247246:
            await message.reply("Please use the 'ParkingSucks GPT Bot' categories for getting parking information.")
            return
        content = message.content.replace(f'<@!{bot.user.id}>', '', 1).lstrip()
        if len(content) > 500:
            await message.reply("Sorry, that message is too long. Try making your message shorter and asking more than one message to get the information you need.")
            return
        response = await call_completion_api(str(message.author), content, str(message.channel.name))
        if 'error' in response:
            await message.reply("Sorry, that didn't work")
        else:
            await message.reply(response)
            # Get the system channel using discord.py
            # system_channel = bot.get_channel(1096444199433408632)

# Run the bot
bot.run(TOKEN)

# Prompt 1:
# Create a python discord bot which:
# - listens for user messages (needs messages intents)
# - takes the message and passes it with the username to a flask API located at 192.168.1.1:8080
# using JSON
# - waits for a response from the API which could take up to 1 minute
# - Replies to the user with the response

# Prompt 2:
# Setup a discord.py bot that prints to the console the invite link
# every user uses to join a server as they join.
# Don't explain, just show code.

# Prompt 3:
# <Gave Code>
# This snippet is returning JSON like this:
# {'error': 'Query not allowed'}
# Change it so instead if 'error' is present it says "Sorry, that didn't work"
# and if it's not present it prints the value of the response only, not the entire formatted json
import discord
import aiohttp
from os import getenv
from discord_log import BotLog
from discord.ext import commands

# Replace 'your_bot_token' with your actual bot token
TOKEN = getenv('DISCORD_TOKEN')
logger = BotLog('discord-bot')

# Set up intents to listen for user messages and member join events
intents = discord.Intents.all()
intents.messages = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix='$', intents=intents)

async def call_completion_api(username, message):
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
            response = await fetch(session, url, api_key, username, message)
        except Exception as e:
            logger.error(f"Error calling completion API: {e}")
            return {'error': 'Error calling completion API'}
        return response

async def fetch(session, url, api_key, username, message):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'api_key': api_key, 'username': username, 'message': message}
    async with session.post(url, headers=headers, data=data) as response:
        return await response.json(content_type=None)


@bot.event
async def on_ready():
    logger.info('Bot is ready and connected.')
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user or 'system' in message.channel.name:
        return

    # Call Flask API with username and message content
    response = await call_completion_api(str(message.author), message.content)

    # Check if response contains an error
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
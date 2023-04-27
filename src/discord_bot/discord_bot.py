import discord
from os import getenv
from utils import call_completion_api, call_parking_api, convert_schedule
from discord_log import BotLog
from discord.ext import commands
import newrelic.agent

newrelic.agent.initialize('/app/newrelic.ini')
# Remove these when you remove call_parking_api

# Replace 'your_bot_token' with your actual bot token
TOKEN = getenv('DISCORD_TOKEN')
logger = BotLog('discord-bot')

# Set up intents to listen for user messages and member join events
intents = discord.Intents.all()
intents.messages = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    logger.info('Bot is ready and connected.')

@newrelic.agent.background_task()
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    if message.content.lower().startswith('ping?'):
        logger.info(f'Ping? Pong! received from {message.author} in {message.channel}')
        await message.reply('pong!')
        return

    if bot.user in message.mentions:
        if message.channel.category_id != 1099892029523247246:
            await message.reply("Please use the 'ParkingSucks GPT Bot' categories for getting parking information.")
            return
        content = message.content.replace(f'<@!{bot.user.id}>', '', 1).lstrip()
        if len(content) > 500:
            await message.reply("Sorry, that message is too long. Try making your message shorter and asking more than one message to get the information you need.")
            return

        response = await call_completion_api(str(message.author), content, str(message.channel.name), message.id)
        if 'error' in response:
            await message.reply("Sorry, that didn't work")
        else:
            await message.reply(response)
    if 'convert-schedule' in message.channel.name:
        logger.info(f'Converting schedule for {message.author} in {message.channel}')
        converted_schedule = convert_schedule(message.content)

        if not converted_schedule:
            converted_schedule = 'Sorry, I could not convert that schedule. Please try again.'
        await message.reply(converted_schedule)
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

            # Get the system channel using discord.py
            # system_channel = bot.get_channel(1096444199433408632)

async def run_bot():
    DISCORD_TOKEN = getenv('DISCORD_TOKEN')
    await bot.start(DISCORD_TOKEN)

if __name__ == '__main__':
    import asyncio
    asyncio.run(run_bot())

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
from quart import Quart, request
from discord_bot import bot, run_bot
from discord import MessageReference
from discord_log import BotLog
import asyncio
from os import getenv
import newrelic.agent

app = Quart(__name__)
logger = BotLog('discord-bot-api')

@newrelic.agent.background_task()
@app.route('/message_user', methods=['POST'])
async def message_user():
    data = await request.json
    message_str = data.get('message_str')
    user_id = data.get('id')

    if not message_str or not user_id:
        logger.error(f'Invalid input: {data}')
        return {"error": "Invalid input"}, 400

    user = await bot.fetch_user(int(user_id))
    if not user:
        logger.error(f'User not found: {user_id}')
        return {"error": "User not found"}, 404

    logger.info(f'Sending message to user {user.name} ({user.id})')
    await user.send(message_str)
    logger.info(f'Message sent successfully')
    return {"success": True}, 200

@newrelic.agent.background_task()
@app.route('/reply', methods=['POST'])
async def reply():
    data = await request.json
    message_str = data.get('message_str')
    message_id = data.get('id')

    if not message_str or not message_id:
        logger.error(f'Invalid input: {data}')
        return {"error": "Invalid input"}, 400

    try:
        print(getenv('DISCORD_SERVER_ID'))
        server = bot.get_guild(int(getenv('DISCORD_SERVER_ID')))
        original_message = None
        for channel in server.channels:
            if not channel.category:
                continue
            logger.info(f'Checking channel {channel.name} ({channel.id})')
            try:
                original_message = await channel.fetch_message(int(message_id))
                break
            except:
                continue
            finally:
                if not original_message:
                    logger.error(f'Message not found: {message_id}')
                    return {"error": "Message not found"}, 404
        channel = original_message.channel
        message_reference = MessageReference(message_id=int(message_id), channel_id=channel.id)
        logger.info(f'Sending message to channel {channel.name} ({channel.id})')
        await channel.send(message_str, reference=message_reference)
    except Exception as e:
        logger.error(f'Error sending message: {e}')
        return {"error": "Error sending message"}, 500

    logger.info(f'Message sent successfully')
    return {"success": True}, 200

async def main():
    app_task = app.run_task(host="0.0.0.0", port=8080)
    bot_task = asyncio.create_task(run_bot())
    await asyncio.gather(app_task, bot_task)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        loop.run_until_complete(bot.close())
        loop.run_until_complete(app.shutdown())
        loop.close()

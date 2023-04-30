from utils import get_prompt, archive_completion, logger, send_reply, get_funny
from parking_chains import parking_chain
from os import getenv
from langchain.chat_models import ChatOpenAI
from langchain.chains import OpenAIModerationChain
import newrelic.agent
import asyncio

# Set up the chat model
chat = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7
    )

@newrelic.agent.background_task()
async def answer_chain(username, question, message_id, user_id, memory, gpt4=False) -> str:
    """
    This function is the main function that is called by the discord bot to get a response to a question.
    It calls the moderation chain, then the gpt chain, then the final answer chain.
    :param username:
    :param question:
    :param message_id:
    :param user_id:
    :param memory:
    :param gpt4:
    :return:
    """
    # Complete GPT driven moderation
    schedule = memory.get_schedule(username)
    is_ok_future, parking_info_future, map_info_future = await asyncio.gather(
        complete_gpt_moderation(await get_prompt(question, 'ok'), username),
        parking_chain(question, schedule=schedule, gpt4=gpt4),
        map_chain(question, schedule=schedule, gpt4=gpt4),
    )

    # Assign a callback to process is_ok and decide whether to proceed with the final answer
    should_proceed, return_message = await process_is_ok(is_ok_future, username, question, memory)
    if not should_proceed:
        return return_message

    parking_info = parking_info_future
    map_info = map_info_future

    return await get_final_answer(question=question, schedule=parking_info, closest_garages=map_info, gpt4=gpt4)


@newrelic.agent.background_task()
async def map_chain(question, schedule, gpt4=False):
    """
    Determine location of places on campus in relation to garages.
    :param question:
    :param schedule:
    :param gpt4:
    :return:
    """
    question = await get_prompt(question, 'map')
    chat.model_name = "gpt-3.5-turbo" if not gpt4 else "gpt-4"
    map_response = chat(question.to_messages())
    # Extract just the text after ":"
    map_response = map_response.content.split(':')[-1]
    #map_response = map_response.content.split('Final Answer: ')[-1]
    logger.info(f'Got map response: {map_response}')
    return map_response
@newrelic.agent.background_task()
async def passed_moderation(query: str) -> bool:
    """
    Complete OpenAI required moderation. Checks for hateful content.
    :param query:
    :return:
    """
    try:
        moderation_chain = OpenAIModerationChain(error=True)
        moderation_chain.run(query)
        logger.info('Moderation chain passed')
        return True
    except ValueError as e:
        logger.error(f"Flagged content detected: {e}")
        logger.error(f"Query: {query}")
        return False

async def process_is_ok(is_ok, username, question, memory):
    # Not allowed
    if is_ok == 0 or not await passed_moderation(question):
        logger.info(f'Message not allowed: {question} (username: {username})')
        current_sched = memory.get_schedule(username)
        # Log bad actor
        if 'Bad Actor Count: ' not in current_sched:
            new_sched = f'{current_sched}\nBad Actor Count: 1'
            count = 1
        else:
            # Increment the number of bad actor counts
            count = int(current_sched.split('Bad Actor Count: ')[-1]) + 1
            # Remove old Bad Actor Count from current_shed to place a new one in
            current_sched = current_sched.split('Bad Actor Count: ')[0]
            new_sched = f'{current_sched}\nBad Actor Count: {count}'
        memory.write_schedule(username, new_sched)
        # determine first/second/third/found string based on count
        return False, 'You\'re not allowed to ask that.' if count == 1 else f"You're not allowed to ask that. I've had to tell you {count} times."

    # Couldn't determine if we can handle this, let's try anyway.
    if is_ok == 2:
        logger.info(f'Trying a command, we shall see. Question: {question}')
    return True, ""

@newrelic.agent.background_task()
async def complete_gpt_moderation(query, username) -> int:
    """
    Complete GPT driven moderation. Checks for unsafe content and ensures we're only talking
    about parking information or universities.
    :param query:
    :param username:
    :return:
    """
    response = chat(query.to_messages()).content
    await archive_completion(query.to_messages(), response)
    logger.info(f'Got response: {response}')

    # Safe
    if '!!!!!!!!' in response:
        logger.info(f'Found a safe query')
        return 1

    # Not sure
    if '########' in response:
        logger.info(f'Found an unsure query')
        return 2

    # Unsafe
    if '@@@@@@@@' in response:
        logger.critical(f"UNSAFE QUERY DETECTED from {username}")
        return 0

    # Unable to parse
    else:
        logger.error(f'Unable to determine safety of query: {query}')
    return 0

@newrelic.agent.background_task()
async def get_final_answer(question, schedule, closest_garages, gpt4=False) -> str:
    """
    This function gets all the available information and forms a response which will
    go directly to the user.
    :param question:
    :param schedule:
    :param closest_garages:
    :param gpt4:
    :return:
    """
    logger.info(f'Getting final answer for question: {question}')
    question = await get_prompt(question, 'final', schedule=schedule, closest_garages=closest_garages)
    chat.model_name = "gpt-3.5-turbo" if not gpt4 else "gpt-4"
    response = chat(question.to_messages()).content

    await archive_completion(question.to_messages(), response)
    return response

@newrelic.agent.background_task()
async def schedule_summarizer(schedule) -> str:
    pass


# Prompt 1:
# Add a flask api to this application. There should be 1 end-point: /completion
# which confirms the API_KEY environment variable matches the api_key argument.
# The 'query' argument should be passed to the 'complete_gpt_moderation' function and if it's ok,
# then to the 'get_sql_query' function. The /completion endpoint should return
# the result of get_sql_query.

# Prompt 2:
# Write python function(s) to call this api with the required parameters and
# decode the response. Update the parking-api.py file as needed.

# Prompt 3:
# <Gave Code>
# <Gave errors>
# <Gave API endpoint code>
# How can I properly decode final_answer in the discord bot to display it in the chat room?

# Prompt 4:
# This function:
# <gave get_sql_query>
# Is taking this response value:
# <Gave example response>
# and not properly returning the extracted SQL query. Fix it, please.

# Prompt 5:
# Take this query and use the CONCAT or similar function to add a single row to the top that says:
# Data generated for Tuesday and Thursday's from 12:30pm until 1:30pm.
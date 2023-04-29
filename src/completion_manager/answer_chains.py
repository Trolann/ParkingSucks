from utils import get_prompt, archive_completion, logger, send_reply, get_funny
from parking_chains import parking_chain
from os import getenv
from langchain.chat_models import ChatOpenAI
from langchain.chains import OpenAIModerationChain
import newrelic.agent
from nr_openai_observability import monitor
from time import sleep

monitor.initialization(getenv('NEW_RELIC_LICENSE_KEY_AI'))
chat = ChatOpenAI(
    openai_api_key=getenv('OPENAI_API_KEY'),
    temperature=0.7
    )

@newrelic.agent.background_task()
async def answer_chain(username, question, message_id, user_id, memory, gpt4=False) -> str:
    is_ok = await complete_gpt_moderation(await get_prompt(question, 'ok'), username)
    if is_ok == 0:
        logger.info(f'Message not allowed: {question} (username: {username})')
        current_sched = memory.get_schedule(username)
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
        return 'You\'re not allowed to ask that.' if count == 1 else f"You're not allowed to ask that. I've had to tell you {count} times."
    if is_ok == 2:
        logger.info(f'Trying a command, we shall see. Question: {question}')

    if gpt4:
        send_reply(get_funny(), message_id)

    schedule = memory.get_schedule(username)
    if schedule == '':
        logger.info(f'No schedule for user {username}')
    else:
        logger.info(f'Got schedule for user {username}')
    parking_info = await parking_chain(question, schedule=schedule, gpt4=gpt4)
    map_info = await map_chain(question, schedule=schedule, gpt4=gpt4)
    return await get_final_answer(question=question, schedule=parking_info, closest_garages=map_info, gpt4=gpt4)

@newrelic.agent.background_task()
async def map_chain(question, schedule, gpt4=False):
    question = await get_prompt(question, 'map')
    chat.model_name = "gpt-3.5-turbo" if not gpt4 else "gpt-4"
    map_response = chat(question.to_messages())
    # Extract just the text after "Final Answer:"
    map_response = map_response.content.split('Final Answer: ')[-1]
    logger.info(f'Got map response: {map_response}')
    return map_response
@newrelic.agent.background_task()
async def complete_moderation(query: str) -> bool:
    try:
        moderation_chain = OpenAIModerationChain(error=True)
        moderation_chain.run(query)
        logger.info('Moderation chain passed')
        return True
    except ValueError as e:
        logger.error(f"Flagged content detected: {e}")
        logger.error(f"Query: {query}")
        return False

@newrelic.agent.background_task()
async def complete_gpt_moderation(query, username) -> int:
    response = chat(query.to_messages()).content
    await archive_completion(query.to_messages(), response)
    logger.info(f'Got response: {response}')
    if '!!!!!!!!' in response:
        logger.info(f'Found a safe query')
        return 1
    if '########' in response:
        logger.info(f'Found an unsure query')
        return 2
    if '@@@@@@@@' in response:
        logger.critical(f"UNSAFE QUERY DETECTED from {username}")
    else:
        logger.error(f'Unable to determine safety of query: {query}')
    return 0

@newrelic.agent.background_task()
async def get_final_answer(question, schedule, closest_garages, gpt4=False) -> str:
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
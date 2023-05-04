from os import getenv
from nr_openai_observability import monitor
monitor.initialization(getenv('NEW_RELIC_LICENSE_KEY_AI'))
from quart import Quart, jsonify, make_response, request
from answer_chains import answer_chain
from completion_log import BotLog
import newrelic.agent
from mariadb import Memory

newrelic.agent.initialize('/app/newrelic.ini')

logger = BotLog('completion-api')
app = Quart(__name__)


@newrelic.agent.background_task()
@app.route('/completion', methods=['POST'])
async def completion():
    """
    Main completion endpoint. This is where the magic happens.
    Returns a final answer to go directly to the end-user.
    :return:
    """
    form = await request.form
    api_key = form.get('api_key')
    username = form.get('username')
    message = form.get('message')
    message_id = form.get('message_id')
    user_id = form.get('user_id')
    channel = form.get('channel', 'asdf')
    logger.info(f'Got request from {username} with message: {message}')

    # AuthN
    if api_key != getenv('API_KEY'):
        logger.error(f'Invalid API key: {api_key} from {request.remote_addr}/{username}')
        return jsonify({'error': 'Invalid API key'}), 401

    # Currently the only way to use GPT4.
    # TODO: Take in model name as parameter
    gpt4 = True

    final_answer = await answer_chain(username, message, message_id=message_id, user_id=user_id, memory=memory, gpt4=gpt4)
    logger.info(f'Got final answer for {username}: {final_answer} ')

    # Prepare response
    response = jsonify(final_answer)
    response.status_code = 200
    response.content_type = 'application/json'
    return response


if __name__ == '__main__':
    memory = Memory()
    app.run(host='0.0.0.0', port=8080, debug=True)

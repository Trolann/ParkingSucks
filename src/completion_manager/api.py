import os
from quart import Quart, jsonify, make_response, request
from answer_chains import answer_chain
from completion_log import BotLog
import newrelic.agent

newrelic.agent.initialize('/app/newrelic.ini')

logger = BotLog('completion-api')
app = Quart(__name__)


@newrelic.agent.background_task()
@app.route('/completion', methods=['POST'])
async def completion():
    form = await request.form
    api_key = form.get('api_key')
    username = form.get('username')
    message = form.get('message')
    channel = form.get('channel', 'asdf')
    logger.info(f'Got request from {username} with message: {message}')

    if api_key != os.getenv('API_KEY'):
        logger.error(f'Invalid API key: {api_key} from {request.remote_addr}/{username}')
        return jsonify({'error': 'Invalid API key'}), 401
    gpt4 = False
    if 'gpt4' in channel:
        logger.info(f'Using GPT4 for {username}')
        gpt4 = True
    final_answer = await answer_chain(username, message, gpt4=gpt4)
    logger.info(f'Got final answer: {final_answer} {type(final_answer)}')
    response = jsonify(final_answer)
    response.status_code = 200
    response.content_type = 'application/json'
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

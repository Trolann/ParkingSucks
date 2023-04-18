import json

from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

def get_prompt(query, prompt_type, results=None):
    '''
    Loads prompt template from file to allow for rapid changing of prompts.
    :param query:
    :return:
    '''
    with open(f'templates/{prompt_type}_system.txt', 'r') as f:
        is_this_ok_template = f.read()

    with open(f'templates/{prompt_type}_human.txt', 'r') as f:
        is_this_ok_human = f.read()

    system_prompt = SystemMessagePromptTemplate.from_template(is_this_ok_template)
    human_prompt = HumanMessagePromptTemplate.from_template(is_this_ok_human)
    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_prompt])

    # TODO: See if this one-liner is needed
    return chat_prompt.format_prompt(query=query) if not results else chat_prompt.format_prompt(query=query, results=results)

def archive_completion(prompt_messages, response):
    '''
    Save a simple text copy of every completion, because they're expensive and we'll probably want them again
    :param prompt_messages:
    :param response:
    :return:
    '''
    with open('logs/completion_archive.txt', 'a') as f:
        f.write("Prompt Messages:\n")
        for prompt in prompt_messages:
            try:
                f.write(json.dumps(prompt, indent=4))
            except TypeError:
                f.write(str(prompt))
            f.write("\n")
        f.write("\nResponse:\n")
        f.write(json.dumps(response, indent=4))
        f.write("\n\n")

# Prompt 1:
# Combine this into the get_final_answer_prompt function and have it load the
# final_answer_template variable from the templates/final_system.txt file and the
# final_answer_human from final_human.txt to allow dynamically loading them.

# Prompt 2:
# put it all in the get_final_answer_prompt method. hardcode the filenames

# Prompt 3:
# Repeated for each item

# Prompt 4: (allows for rapid update of .txt files)
# Write a bash script that monitors the directory ~/templates and whenever a
# file is updated, it scp copies that file using the .ssh/parkinsucks.pem key
# to root@192.168.8.8 in the /root/docker/templates directory, overwriting any file there.

# Prompt 5:
# how can I have this script run at startup and run in the background?


# Prompt 6:
# sent 218 bytes  received 12 bytes  460.00 bytes/sec
# total size is 3,606  speedup is 15.68
# ./sync_files.sh: line 15: inotifywait: command not found
# sending incremental file list

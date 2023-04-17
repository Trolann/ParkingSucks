from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

def get_safety_prompt(query):
    '''
    Loads prompt template from file to allow for rapid changing of prompts.
    :param query:
    :return:
    '''
    with open('templates/ok_system.txt', 'r') as f:
        is_this_ok_template = f.read()

    with open('templates/ok_human.txt', 'r') as f:
        is_this_ok_human = f.read()

    is_this_ok_system_prompt = SystemMessagePromptTemplate.from_template(is_this_ok_template)
    is_this_ok_human_prompt = HumanMessagePromptTemplate.from_template(is_this_ok_human)
    is_this_ok_chat_prompt = ChatPromptTemplate.from_messages([is_this_ok_system_prompt, is_this_ok_human_prompt])

    return is_this_ok_chat_prompt.format_prompt(query=query)

def get_sql_gen_prompt(message):
    '''
    Loads prompt template from file to allow for rapid changing of prompts.
    :param query:
    :return:
    '''
    with open('templates/sql_system.txt', 'r') as f:
        sql_gen_template = f.read()

    with open('templates/sql_human.txt', 'r') as f:
        sql_gen_human = f.read()

    sql_gen_system_prompt = SystemMessagePromptTemplate.from_template(sql_gen_template)
    sql_gen_human_prompt = HumanMessagePromptTemplate.from_template(sql_gen_human)
    sql_gen_chat_prompt = ChatPromptTemplate.from_messages([sql_gen_system_prompt, sql_gen_human_prompt])

    return sql_gen_chat_prompt.format_prompt(question=message)

def get_final_answer_prompt(message, results):
    '''
    Loads prompt template from file to allow for rapid changing of prompts.
    :param query:
    :return:
    '''
    with open('templates/final_system.txt', 'r') as f:
        final_answer_template = f.read()

    with open('templates/final_human.txt', 'r') as f:
        final_answer_human = f.read()

    final_answer_system_prompt = SystemMessagePromptTemplate.from_template(final_answer_template)
    final_answer_human_prompt = HumanMessagePromptTemplate.from_template(final_answer_human)
    final_answer_chat_prompt = ChatPromptTemplate.from_messages([final_answer_system_prompt, final_answer_human_prompt])

    return final_answer_chat_prompt.format_prompt(message=message, results=results)

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

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

import urllib3
import certifi
from random import choice
import sqlite3
from time import sleep, time
from shutil import copy2 as copyfile
from os import environ
from os.path import exists

try:
    path = environ['DIR_PATH']
    print('path: {}'.format(path))
except KeyError:
    path = ''
    print('path: local'.format(path))

garage_website = 'http://sjsuparkingstatus.sjsu.edu/GarageStatus'
db_location = '{}/db/db.db'.format(path)
db_table = 'parking'

if not exists(db_location):
    print('doesn\'t exist')
    copyfile('{}db.db'.format(environ['DIR_PATH']), environ['DIR_PATH'] + 'db/')
else:
    print('does exist')

def _insert(cursor, sql):
    '''Recursive insert wrapper to avoid DB collisisons'''
    try:
        cursor.execute(sql)
    except sqlite3.OperationalError:
        # Chill for 2 seconds then recur
        sleep(2)
        _insert(cursor, sql)


def insert(db, table, tup_insert, commit_to_db = True):
    '''Inserts into sqlite db with the option:value schema
        Recursively calls _insert wrapper to avoid collisions/locked db'''
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    sql = 'INSERT OR REPLACE INTO {} VALUES {}'.format(table, tup_insert)
    _insert(cursor, sql)  # Wrapper for recursion
    if commit_to_db:
        connection.commit()
    cursor.close()
    connection.close()


def get_site(url):
    user_agent_list = (
        # Chrome
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        # Firefox
        'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
    )
    user_agent = choice(user_agent_list)
    http = urllib3.PoolManager(
        cert_reqs='CERT_REQUIRED',
        ca_certs=certifi.where(),
        headers={'User-Agent': user_agent, "Accept-Language": "en-US, en;q=0.5"}
    )
    page = http.request('GET', url)
    return str(page._body)


class Garage:
    def __init__(self, website_html, start_index):
        self.item_start_str = 'product type-product'  # Generates an item's start_index in Deal object
        self.name_str = { '<a data-garagename=\"\">': ' </a>' }
        self.address_str = { 'style=\"width:15px;\"> ': '</a><span' }
        self.full_str_start = { '<span data-garagefullness=\"\"> </span>': ' %  full' }
        self.name = ''
        self.address = ''
        self.fullness = ''
        self.last_timestamp = ''
        self.update(website_html, start_index)


    def update(self, website_html, start_index):
        tup = (self.name_str, self.address_str, self.full_str_start)
        final = list()
        for dic in tup:
            for key in dic:
                item = key
                terminal = dic[key]
                value = website_html[website_html.find(item, start_index) + len(item): website_html.find(terminal, website_html.find(item, start_index) + len(item))]
                value = '100' if 'ull' in value else value
                full_val = True
                if 'arage' in value:
                    self.name = value
                    full_val = False
                if 'ose' in value:
                    self.address = value
                    full_val = False
                if full_val:
                    self.fullness = value
            self.last_timestamp = time()


def get_all_deals(website):
    item_start_str = '<garage>'
    garages = []

    # Get a copy of the source
    html = get_site(website)

    start_index = html.find(item_start_str)
    while start_index != -1:
        garage = Garage(html, start_index)
        print(garage.name)
        print(garage.address)
        print(garage.fullness)
        print(garage.last_timestamp)

        garages.append(garage)
        start_index = html.find(item_start_str, start_index + 1)

    return garages


def process_deals(db, table):  # Take old list, get new list, produce print/expired/update the old list
    global garage_website

    garages = get_all_deals(garage_website)

    for garage in garages:
        timestamp, name, address, fullness = garage.last_timestamp, garage.name, garage.address, garage.fullness
        insert_tuple = (timestamp, name, address, fullness)
        insert(db, table, insert_tuple)



def garage_daemon(sleep_time):
    print('Garage Daemon started')

    while True:
        process_deals(db_location, db_table)
        sleep(sleep_time)


garage_daemon(15)

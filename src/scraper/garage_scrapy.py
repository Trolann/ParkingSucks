import requests
from bs4 import BeautifulSoup
from datetime import datetime
from agent_picker import random_ua
from garage import Garage
from src.mariadb import Config
from time import sleep


def get_site(site_url):
    headers = {'User-Agent': random_ua()[0], "Accept-Language": "en-US, en;q=0.5"}
    page = requests.get(site_url, headers=headers, verify=False)
    return page.content.decode('utf-8')


def get_garage_info(garage_url):
    # Make a GET request to the URL
    response = get_site(garage_url)

    # Parse the HTML using Beautiful Soup
    soup = BeautifulSoup(response, 'html.parser')

    # Extract the timestamp
    timestamp_elem = soup.find('p', class_='timestamp')
    timestamp_str = timestamp_elem.text.replace('Last updated ', '').replace(' Refresh', '')
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %I:%M:%S %p').isoformat()

    # Extract the garage information
    garages = []
    garage_elems = soup.find_all('h2', class_='garage__name')
    for garage_elem in garage_elems:
        name = garage_elem.text.rstrip()
        address_elem = garage_elem.find_next('a', class_='garage__address')
        address = address_elem['href'].split('place/')[1]
        fullness_elem = address_elem.find_next('span', class_='garage__fullness')
        fullness = int("".join(x for x in fullness_elem.text if x in '0123456789')) if 'Full' not in fullness_elem.text else 100
        garages.append(Garage(name, address, fullness, timestamp))

    return garages


if __name__ == '__main__':
    url = "https://sjsuparkingstatus.sjsu.edu/"
    garage_db = Config('sjsu')
    for garage in get_garage_info(url):
        print(f'New garage: {garage}')
        garage_db.new(garage)
    sleep(60 * 5)

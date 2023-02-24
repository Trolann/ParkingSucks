import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib3 import PoolManager
from certifi import where as certifi_where
from ssl import create_default_context as create_ssl_context
from agent_picker import random_ua
from garage import Garage
from mariadb import Config

garage_db = Config('test')

def get_site(site_url):
    http = PoolManager(
        cert_reqs='CERT_REQUIRED',
        ca_certs=certifi_where(),
        ssl_context=create_ssl_context(),
        headers={'User-Agent': random_ua()[0], "Accept-Language": "en-US, en;q=0.5"}
    )
    page = http.request('GET', site_url)
    return str(page._body)


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
        name = garage_elem.text
        address_elem = garage_elem.find_next('a', class_='garage__address')
        address = address_elem['href'].split('place/')[1]
        fullness_elem = address_elem.find_next('span', class_='garage__fullness')
        fullness = int("".join(x for x in fullness_elem.text if x in '0123456789'))
        garages.append(Garage(name, address, fullness, timestamp))

    return garages


if __name__ == '__main__':
    url = "https://sjsuparkingstatus.sjsu.edu/"
    for garage in get_garage_info(url):
        garage_db.new(garage)
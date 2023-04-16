import requests
from bs4 import BeautifulSoup
from datetime import datetime
from agent_picker import random_ua
from garage import Garage
from mariadb import Config
from time import sleep
from scraper_log import BotLog

logger = BotLog('garage_scrapy')


def get_site(site_url):
    """
    This function takes in a url and makes a GET request to the URL using a random user agent
    Returns the content of the page as a string in utf-8 format.
    """
    headers = {'User-Agent': random_ua()[0], "Accept-Language": "en-US, en;q=0.5"}
    page = requests.get(site_url, headers=headers, verify=False)
    logger.info(f'GET request to {site_url} returned {page.status_code} status code.')
    return page.content.decode('utf-8')


def get_garage_info(garage_url):
    """
    This function takes in a garage url and extracts the garage information from the site
    Returns a list of Garage objects
    """
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
    logger.info(f'Extracting info for {len(garage_elems)} garages.')
    for garage_elem in garage_elems:
        name = garage_elem.text.rstrip()
        logger.info(f'Extracting info for {name} garage.')
        address_elem = garage_elem.find_next('a', class_='garage__address')
        address = address_elem['href'].split('place/')[1]
        fullness_elem = address_elem.find_next('span', class_='garage__fullness')
        # Extract fullness                                   as an integer              they use "Full" instead of 100 cause they suck, obviously
        fullness = int("".join(x for x in fullness_elem.text if x in '0123456789')) if 'Full' not in fullness_elem.text else 100
        garages.append(Garage(name, address, fullness, timestamp))
    logger.info(f'Extracted info for garages: {",".join([garage.name for garage in garages])}')
    # Prompt for the above:
    # Give me a one-liner that takes in garage objects and joins garage names together with a comma
    return garages


if __name__ == '__main__':
    url = "https://sjsuparkingstatus.sjsu.edu/"
    garage_db = Config('sjsu')
    number_new = 0
    for garage in get_garage_info(url):
        logger.info(f'New garage: {garage}')
        added_new = garage_db.new(garage)
        number_new += 1 if added_new else 0
    logger.info(f'Scraped {number_new} new garages.')
    # Wait for 5 minutes before running again
    logger.info('Waiting 5 minutes before running again...')
    sleep(60 * 5)

import re
from datetime import datetime, timedelta
from scraper_log import BotLog
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor
import pytz
import newrelic.agent

logger = BotLog("shuttle_scrape")

class ShuttleStatus:
    """
    Class to represent the status of a shuttle stop
    """
    def __init__(self, stop_url, stop_name=None, time_to_departure=None, updated_at=None):
        """
        :type stop_url: str
        :type stop_name: str
        :type time_to_departure: int
        :type updated_at: datetime
        :param stop_url:
        :param stop_name:
        :param time_to_departure:
        :param updated_at:
        """
        self.stop_url = stop_url
        self.stop_name = stop_name
        self.updated_at = updated_at
        self.time_to_departure = time_to_departure
        self.next_shuttle_times = []
        self.old_time_to_departure = 0
        self.time_to_departure = 0

    @newrelic.agent.background_task()
    def scrape_data(self):
        """
        Scrape the shuttle status from the stop_url
        :return:
        """
        logger.info(f'Starting scrape of {self.stop_url}')

        # Use Selenium to scrape the page
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        chrome_service = Service(executable_path='/usr/bin/chromedriver')
        chrome_service.command_line_args().append('--headless')
        chrome_service.command_line_args().append('--no-sandbox')
        chrome_service.command_line_args().append('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=chrome_service, options=options)

        # Get the webpage or error out
        try:
            driver.get(self.stop_url)
            WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='stop-departures-list']/li")))
            soup = BeautifulSoup(driver.page_source, "html.parser")
        except Exception as e:
            logger.error(f'Error scraping {self.stop_url}: {e}')
            return
        finally:
            driver.quit()

        logger.info(f'Selenium scrape of {self.stop_url} complete')

        # Find and parse timestamp
        timestamp_text = soup.find("p", {"id": "infobox"}).text
        timestamp_text = re.sub(r'\s\([A-Za-z\s]+\)$', '', timestamp_text)  # Remove timezone
        timestamp_text = timestamp_text.replace("GMT", "")  # Remove "GMT" from the timezone offset
        timestamp_format = "Last updated %a %b %d %Y %H:%M:%S %z"
        self.updated_at = datetime.strptime(timestamp_text, timestamp_format)

        # Convert the timestamp to Pacific Time (PT)
        utc_timezone = pytz.timezone("UTC")
        pt_timezone = pytz.timezone("America/Los_Angeles")
        self.updated_at = self.updated_at.replace(tzinfo=utc_timezone).astimezone(pt_timezone)

        # Find and parse stop name
        stop_name_text = soup.find("h2").text
        self.stop_name = stop_name_text.replace("Next departures for ", "").strip()
        logger.info(f'Stop name: {self.stop_name}')

        # Find and parse next departure times
        next_departures = soup.find_all("li", {"class": "eta-route"})
        if len(next_departures) > 0:
            departure = next_departures[0]
            try:
                logger.info(f'Departure information: {departure.text.lower()}')
                if "no etas currently available" in departure.text.lower():
                    time_to_departure = -1
                elif "now" in departure.text.lower():
                    time_to_departure = 0
                else:
                    time_to_departure = int(re.search(r"\d+(?=\sminutes)", departure.text).group())
                self.time_to_departure = time_to_departure
                logger.info(f'Time to departure for {self.stop_name}: {time_to_departure} minutes')
                if time_to_departure >= 0:
                    next_departure_time = self.updated_at + timedelta(minutes=time_to_departure)
                    self.next_shuttle_times.append(next_departure_time)
            except AttributeError as a:
                logger.error(f"Error parsing next departure times: {a}")
                logger.info(f'Departure information: {departure.text}')
        else:
            self.time_to_departure = -1
            self.next_shuttle_times = []
            logger.info(f'No departure information found for {self.stop_name}')

@newrelic.agent.background_task()
def monitor_shuttle_statuses(shuttle_db):
    """
    Monitor shuttle statuses in a loop and log a new ETA whenever the current ETA is > 2
    minutes greater than the previous time, or whenever an ETA is first reported or observed
    as unavailable.

    Expected to run in a thread with exception handling and restarts.

    :type shuttle_db: ShuttleDB
    :param shuttle_db:
    :return:
    """
    stop1 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=1")
    stop5 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=5")
    shuttles = [stop1, stop5]

    # Ensure the first scrape is sent to the DB
    prev_time_to_departure = [-1000] * len(shuttles)

    while True:
        # Use ThreadPoolExecutor to run the scrapes in separate threads
        with ThreadPoolExecutor(max_workers=len(shuttles)) as executor:
            scrape_futures = [executor.submit(shuttle.scrape_data) for shuttle in shuttles]
            for future in scrape_futures:
                future.result()

        # Check if the time_to_departure has increased by more than 5 points for each stop
        for idx, shuttle in enumerate(shuttles):
            logger.info(f'Previous time to departure for {shuttle.stop_name}: {prev_time_to_departure[idx]} minutes')
            logger.info(f'Current time to departure for {shuttle.stop_name}: {shuttle.time_to_departure} minutes')

            # If the time_to_departure has increased by more than 2 minutes, or if the time_to_departure
            # has changed from a valid value to an invalid value, log the new time_to_departure
            if (shuttle.time_to_departure - prev_time_to_departure[idx] > 2 and shuttle.time_to_departure != 0) or \
               (shuttle.time_to_departure == -1 and prev_time_to_departure[idx] != -1):
                # Log the new time_to_departure
                shuttle_db.insert_data(shuttle.stop_name, shuttle.time_to_departure, shuttle.updated_at)
                logger.info(f'New shuttle time for {shuttle.stop_name}: {shuttle.time_to_departure} minutes')
            prev_time_to_departure[idx] = shuttle.time_to_departure

        sleep(60)



if __name__ == "__main__":
    stop1 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=1")
    stop5 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=5")
    monitor_shuttle_statuses()


# Prompts

# Write a python script with a main dunder method to go to http://sjsu.doublemap.com/map/text?stop=5 and http://sjsu.doublemap.com/map/text?stop=1 and has functions to:
# 1) Find the current timestamp written on the page (rendered javascript) as Last updated Tue Apr 25 2023 13:50:26 GMT-0700 (Pacific Daylight Time). Store as a datetime object for use soon
# 2) Scrape the stop name and time until next departure from the stop written on the page (rendered javascript):
# Next departures for ALMA STOP
#
#     Spring 2023: 19 minutes
#     Spring 2023: 27 minutes
# 3) Computes a list of times for 'next shuttle times' as datetime objects and the next time a shuttle will come
# 4) Determine the min, max, mean time a shuttle will depart based on new information.
# 5) Keeps as little information as possible
# 6) Stores all of this in some kind of ShuttleStatus class which we can use to get information on stops and shuttles

# Traceback (most recent call last):
#   File "main.py", line 46, in <module>
#     stop1 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=1")
#   File "main.py", line 14, in __init__
#     self.scrape_data()
#   File "main.py", line 21, in scrape_data
#     timestamp_text = soup.find("span", {"id": "lastUpdated"}).text
# AttributeError: 'NoneType' object has no attribute 'text'

# Looking into my monitoring I'm seeing dozens of open ports on localhost, which appear to be associated with urrlib2. Sometimes it seems these ports are being exhausted and throwing errors.
#
# How can I modify my code to better manage the ports being used and prevent resource exhaustion?

# Are there going to be any issues with ThreadPool by using a single driver? Why doesn't the driver.quit() in the ShuttleStatus class currently cleanup the ports?

#        try:
#             driver.get(self.stop_url)
#             WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='stop-departures-list']/li")))
#             soup = BeautifulSoup(driver.page_source, "html.parser")
#         except Exception as e:
#             logger.error(f'Error scraping {self.stop_url}: {e}')
#             return
#         finally:
#             driver.quit()
#
# Will this properly hit .quit() or will the return in the exeption block prevent it?

#This script is incorrectly displaying the time to departure. From the website (stop1):
#  DoubleMap
# Next departures for Duncan Hall
#
#     Spring 2023: 23 minutes
#     Spring 2023: 39 minutes
#
# Last updated Tue Apr 25 2023 15:46:19 GMT-0700 (Pacific Daylight Time)
#
# (stop5)
#
# DoubleMap
# Next departures for ALMA STOP
#
#     Spring 2023: 27 minutes
#     Spring 2023: 37 minutes
#
# Last updated Tue Apr 25 2023 15:46:27 GMT-0700 (Pacific Daylight Time)
#
# As
# Updated time_to_departure for stop 1: 2023 minutes
# Updated time_to_departure for stop 5: 2023 minutes

# Move the while loop to a function. Also add to the function logic to sleep for the minimum given time minus 2 minutes and then if the min sleep time is less than 2 minutes to sleep for 10 seconds.
#
# The function should take in a list of ShuttleStatus objects


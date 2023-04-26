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
    def __init__(self, stop_url, stop_name=None, time_to_departure=None, updated_at=None):
        self.stop_url = stop_url
        self.stop_name = stop_name
        self.updated_at = updated_at
        self.time_to_departure = time_to_departure
        self.next_shuttle_times = []
        self.old_time_to_departure = 0
        self.time_to_departure = 0

    @newrelic.agent.background_task()
    def scrape_data(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        chrome_service = Service(executable_path='/usr/bin/chromedriver')
        chrome_service.command_line_args().append('--headless')
        chrome_service.command_line_args().append('--no-sandbox')
        chrome_service.command_line_args().append('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=chrome_service, options=options)
        driver.get(self.stop_url)

        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, "//ul[@id='stop-departures-list']/li")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

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

        # Find and parse next departure times
        next_departures = soup.find_all("li", {"class": "eta-route"})
        if len(next_departures) > 0:
            departure = next_departures[0]
            try:
                if "now" in departure.text.lower():
                    time_to_departure = 0
                else:
                    time_to_departure = int(re.search(r"\d+(?=\sminutes)", departure.text).group())
                self.time_to_departure = time_to_departure
                next_departure_time = self.updated_at + timedelta(minutes=time_to_departure)
                self.next_shuttle_times.append(next_departure_time)
            except AttributeError as a:
                logger.error(f"Error parsing next departure times: {a}")
                logger.info(f'Departure information: {departure.text}')

@newrelic.agent.background_task()
def monitor_shuttle_statuses(shuttle_db):
    stop1 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=1")
    stop5 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=5")
    shuttles = [stop1, stop5]
    prev_time_to_departure = [-1000] * len(shuttles)

    while True:
        # Use ThreadPoolExecutor to run the scrapes in separate threads
        with ThreadPoolExecutor(max_workers=len(shuttles)) as executor:
            scrape_futures = [executor.submit(shuttle.scrape_data) for shuttle in shuttles]
            for future in scrape_futures:
                future.result()

        # Check if the time_to_departure has increased by more than 5 points for each stop
        for idx, shuttle in enumerate(shuttles):
            if shuttle.time_to_departure - prev_time_to_departure[idx] > 2 and shuttle.time_to_departure != 0:
                shuttle_db.insert_data(shuttle.stop_name, shuttle.time_to_departure, shuttle.updated_at)
                logger.info(f'New shuttle time for {shuttle.stop_name}: {shuttle.time_to_departure} minutes')
            prev_time_to_departure[idx] = shuttle.time_to_departure

        sleep(60)


if __name__ == "__main__":
    stop1 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=1")
    stop5 = ShuttleStatus("http://sjsu.doublemap.com/map/text?stop=5")
    monitor_shuttle_statuses()

import unittest
import requests
from datetime import datetime, timedelta
from garage_scrapy import get_garage_info, Garage


class TestGetGarageInfo(unittest.TestCase):
    def test_garage_names(self):
        garage_url = "https://sjsuparkingstatus.sjsu.edu/"
        garage_url = garage_url  # Replace with the actual URL
        garages = get_garage_info(garage_url)
        expected_names = ["South Garage", "North Garage", "West Garage", "South Campus Garage"]
        returned_names = [garage.name for garage in garages]

        # Ensure that each expected name is in the returned names and vice versa
        for name in expected_names:
            self.assertIn(name, returned_names)
        for name in returned_names:
            self.assertIn(name, expected_names)

        # Ensure that there's a 1:1 correspondence between the garages returned and the expected garage names
        self.assertEqual(len(garages), len(expected_names))
        self.assertEqual(len(set(returned_names)), len(expected_names))

    def test_fullness_range(self):
        garage_url = "https://sjsuparkingstatus.sjsu.edu/"
        garage_url = garage_url  # Replace with the actual URL
        garages = get_garage_info(garage_url)
        for garage in garages:
            self.assertGreaterEqual(garage.fullness, 0)
            self.assertLessEqual(garage.fullness, 100)

    def test_timestamp(self):
        garage_url = "https://sjsuparkingstatus.sjsu.edu/"
        garage_url = garage_url  # Replace with the actual URL
        garages = get_garage_info(garage_url)
        now = datetime.now().isoformat()
        six_hours_ago = (datetime.now() - timedelta(hours=6)).isoformat()
        for garage in garages:
            self.assertGreaterEqual(garage.timestamp, six_hours_ago)
            self.assertLessEqual(garage.timestamp, now)

class TestURLStatusCodes(unittest.TestCase):

    def test_url_status_codes(self):
        urls = [
            "https://www.parkingsucks.com",
            "http://www.parkingsucks.com",
            "https://parkingsucks.com",
            "http://parkingsucks.com",
        ]

        for url in urls:
            response = requests.get(url)
            self.assertEqual(response.status_code, 200, f"URL: {url} returned a non-200 status code")

if __name__ == "__main__":
    unittest.main()

# GPT-4 Prompt:
# Gave the entire codebase and said:
# Write unit tests that ensure the garage names are in the list South Garagem North Garage, West Garage,
# South Campus Garage, and that the fullness is between 0 and 100, and that the timestamp is within the last 6 hours.

# GPT-4 Prompt:
# Write a unittest that will query parkingsucks.com and ensure that the status code is 200.
import unittest
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


if __name__ == "__main__":
    unittest.main()

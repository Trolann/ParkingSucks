# SJSU Parking Scraper

This is a simple program designed to be ran as a docker container
in conjunction with a Grafana instance.

This program:
 - Initializes itself and attempts to use the existing SQLite database
 - Created a database if no existing database exists
 - Chooses a random user agent and gets a certificate
 - Scrapes garage name, address and % full
 - Inserts value with current timestamp into the database

Data scraped from [SJSU Parking Spots](http://sjsuparkingstatus.sjsu.edu/GarageStatus)

[Buy me a coffee](https://buymeacoffee.com/trolan) 
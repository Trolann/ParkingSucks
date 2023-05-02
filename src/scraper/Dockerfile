# Use the scraper-base image as a parent image to allow for rapid changes
# Selenium in the base image leads to long build times
FROM trolann/scraper-base:latest

COPY . /app

CMD [ "garage_scrapy.py" ]
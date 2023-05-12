# Use the scraper-base image as a parent image to allow for rapid changes
# Selenium in the base image leads to long build times
FROM trolann/scraper-base:latest

COPY . /app

CMD [ "garage_scrapy.py" ]

# Prompt to split:
# One base image 'scraper-base' which has all the dependencies and such in it with an entrypoint and another which copies the code and uses 'scraper-base:latest' from the local images and copies code files over to allow for more rapid building of the container. Give me the commands to build the image locally too

#prompt to make:
# Make a dockerfile for this script:
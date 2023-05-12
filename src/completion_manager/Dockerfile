# Use the completion-base image as a parent image to allow for rapid changes
FROM trolann/completion-base:latest

# Set the working directory to /app
WORKDIR /app
RUN mkdir /app/logs
RUN mkdir /app/templates
RUN pip install pytz
RUN pip install Levenshtein
# Copy the current directory contents into the container at /app
COPY . /app
# Prompt to split:
# One base image 'scraper-base' which has all the dependencies and such in it with an entrypoint and another which copies the code and uses 'scraper-base:latest' from the local images and copies code files over to allow for more rapid building of the container. Give me the commands to build the image locally too

#prompt to make:
# Make a dockerfile for this script:
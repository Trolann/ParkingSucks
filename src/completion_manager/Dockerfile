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

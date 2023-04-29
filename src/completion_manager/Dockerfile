# Use the completion-base image as a parent image
FROM trolann/completion-base:latest

# Set the working directory to /app
WORKDIR /app
RUN mkdir /app/logs
RUN mkdir /app/templates

# Copy the current directory contents into the container at /app
COPY . /app

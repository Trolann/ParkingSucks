# Use the official Python image as the base image, no complex dependencies to install and depdendncies don't change.
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install newrelic

# Create a directory for logs inside the container
RUN mkdir /app/logs

# Copy the rest of the application code
COPY . .

# Run the bot
CMD ["python", "api.py"]

#prompt to make:
# Make a dockerfile for this script:
# Use the official Python image as the base image, no complex dependencies to install and depdendncies don't change.
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install newrelic

RUN mkdir /app/logs
COPY . /app


CMD ["python", "api.py"]


#prompt to make:
# Make a dockerfile for this script:
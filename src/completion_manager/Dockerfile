# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /app
WORKDIR /app
RUN mkdir /app/logs
RUN mkdir /app/templates

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt
RUN pip install newrelic

# Set completions.py as the entrypoint
ENTRYPOINT ["python", "api.py"]

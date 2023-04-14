# Use the official Python image as the base image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy requirements.txt into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for logs inside the container
RUN mkdir /app/logs

# Copy the rest of the application code
COPY . .

# Run the bot
CMD ["python", "discord_bot.py"]

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into the container
COPY . .

# Expose the port your app runs on
EXPOSE 8000

# Command to run the Django application
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
# Use the official lightweight Python image.
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file initially for caching dependencies
COPY requirements.txt .

RUN apt-get update && apt-get install -y libpq-dev gcc

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
# This tells Django to use production settings
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=backend.settings

# Expose the port that the app runs on
EXPOSE 8000

# Run the application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi:application"]
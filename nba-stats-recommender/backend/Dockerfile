# Use the official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /backend

# Copy only the requirements file first (for caching)
COPY requirements.txt /backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY . /backend

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput

# Expose the port the app runs on
EXPOSE 8000

# Use a non-root user for security
RUN adduser --disabled-password appuser
USER appuser

# Run the application
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
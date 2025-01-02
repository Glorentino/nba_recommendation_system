# Use the official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /backend

# Copy the requirements file and install dependencies
COPY backend/requirements.txt /backend/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY backend /backend

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
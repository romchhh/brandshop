# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY ./requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the docker-entrypoint.sh script and apply permissions
COPY ./docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Copy the rest of the project files
COPY . .

# Expose port
EXPOSE 8000

# Run Django with Gunicorn
ENTRYPOINT ["/app/docker-entrypoint.sh"]

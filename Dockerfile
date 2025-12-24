FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-azure.txt .
RUN pip install --no-cache-dir -r requirements-azure.txt

# Copy application code
COPY vehicle_intelligence/ ./vehicle_intelligence/

# Set environment variables
ENV DJANGO_SETTINGS_MODULE=vehicle_intelligence.settings_production
ENV PYTHONPATH=/app

# Collect static files
RUN cd vehicle_intelligence && python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Start application
CMD ["gunicorn", "--chdir", "vehicle_intelligence", "--bind", "0.0.0.0:8000", "vehicle_intelligence.wsgi:application"]
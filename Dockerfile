# Use official Python image as the base
FROM python:3.11.4-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libgomp1 \
    libatlas3-base \
    libopenblas-dev \
    curl \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install Python dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Make the entrypoint script executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the Django default port
EXPOSE 8000

# Do a services healthcheck
HEALTHCHECK CMD curl -f http://localhost:8000/ || exit 1

# Use entrypoint script to run different services based on CMD argument
ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
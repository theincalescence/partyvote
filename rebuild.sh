#!/bin/bash

# Script to rebuild docker container with error handling
# Usage: ./rebuild.sh

echo "Starting docker container rebuild process..."

# Stop and remove containers
echo "Step 1: Stopping and removing docker containers..."
if ! docker compose down --remove-orphans; then
    echo "Error: Failed to stop and remove containers"
    exit 1
fi

# Build container with no cache
echo "Step 2: Building docker container with no cache..."
if ! docker compose build --no-cache; then
    echo "Error: Failed to build docker container"
    exit 1
fi

# Start containers in detached mode
echo "Step 3: Starting docker containers in detached mode..."
if ! docker compose up -d; then
    echo "Error: Failed to start docker containers"
    exit 1
fi

echo "Docker container rebuild completed successfully!"
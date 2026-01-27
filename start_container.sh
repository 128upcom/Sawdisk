#!/bin/bash
cd "$(dirname "$0")"
docker compose up -d --build
echo "Container started! Check status with: docker ps"
echo "View logs with: docker logs ocelot-python"
echo "Access the web app at: http://localhost:5000"

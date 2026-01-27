#!/bin/bash
# SawDisk Startup Script

echo "🔧 Starting SawDisk Environment..."

# Build Docker containers
echo "🐳 Building Docker containers..."
docker-compose build

# Start containers
echo "🚀 Starting containers..."
docker-compose up -d

# Wait for container to be ready
echo "⏳ Waiting for container to be ready..."
sleep 5

# Show status
echo "📊 Container Status:"
docker-compose ps

# Show logs
echo "📝 Container Logs:"
docker-compose logs --tail=20 python

echo ""
echo "🌐 SawDisk Web Interface:"
echo "   Dashboard: http://localhost:5000"
echo "   Scan Page: http://localhost:5000/scan"
echo "   Alternative Port: http://localhost:8080"
echo ""
echo "💡 Optional CLI Usage:"
echo "   docker-compose exec python python workspace/SawDisk/main.py --help"
echo ""
echo "🔍 To run test scan:"
echo "   docker-compose exec python python test_sawdisk.py"
echo "   docker-compose exec python python workspace/SawDisk/main.py -p /tmp/sawdisk_test"

#!/bin/bash

# Configuration
IP="192.168.1.72"
BACKEND_PORT="8000"
FRONTEND_PORT="3000"

# Set API URL for the frontend to talk to the backend
export NEXT_PUBLIC_API_URL="http://$IP:$BACKEND_PORT"

echo "=================================================="
echo "🚀 Starting Mobile Development Environment"
echo "=================================================="
echo "📡 Backend URL set to: $NEXT_PUBLIC_API_URL"
echo "📱 Access the app on your phone at:"
echo "   http://$IP:$FRONTEND_PORT"
echo "=================================================="
echo "⚠️  Make sure your phone is on the same Wi-Fi network."
echo "⚠️  Make sure the backend is running (uvicorn ... --host 0.0.0.0)"
echo "=================================================="

# Check if qrencode is installed and print QR code
if command -v qrencode &> /dev/null; then
    echo "📱 Scan this QR code to open the app:"
    qrencode -t ANSI "http://$IP:$FRONTEND_PORT"
    echo "=================================================="
fi

# Navigate to frontend directory
cd "$(dirname "$0")/../frontend" || exit

# Start the frontend server
echo "Starting frontend server..."
npm run dev -- --hostname 0.0.0.0

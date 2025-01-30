#!/bin/bash

# Start server
echo "Starting server"

fastapi run api/main.py --port 8080 --proxy-headers

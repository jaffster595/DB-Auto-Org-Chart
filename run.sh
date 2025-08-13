#!/bin/bash
# run.sh - Unix/Linux/Mac startup script

echo "Starting DB AutoOrgChart with Gunicorn..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Start Gunicorn with configuration
echo "Starting Gunicorn server..."
gunicorn --config gunicorn_config.py app:app
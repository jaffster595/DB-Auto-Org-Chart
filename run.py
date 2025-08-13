#!/usr/bin/env python
"""
Cross-platform production server runner
Automatically detects the OS and uses the appropriate WSGI server:
- Gunicorn for Unix/Linux/Mac
- Waitress for Windows
"""

import sys
import platform
import subprocess
import os

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def run_gunicorn():
    """Run the app with Gunicorn (Unix/Linux/Mac)"""
    print("Starting application with Gunicorn...")
    try:
        subprocess.run(["gunicorn", "--config", "gunicorn_config.py", "app:app"])
    except FileNotFoundError:
        print("Gunicorn not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gunicorn"])
        subprocess.run(["gunicorn", "--config", "gunicorn_config.py", "app:app"])

def run_waitress():
    """Run the app with Waitress (Windows)"""
    print("Starting application with Waitress...")
    try:
        subprocess.run([sys.executable, "run_waitress.py"])
    except FileNotFoundError:
        print("Waitress not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "waitress"])
        subprocess.run([sys.executable, "run_waitress.py"])

def main():
    """Main function to detect OS and run appropriate server"""
    
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Install requirements if needed
    try:
        import flask
        import requests
        import schedule
    except ImportError:
        install_requirements()
    
    # Detect OS and run appropriate server
    system = platform.system()
    
    print(f"Detected OS: {system}")
    print("-" * 50)
    
    if system == "Windows":
        print("Using Waitress WSGI server (Windows-compatible)")
        run_waitress()
    else:
        print("Using Gunicorn WSGI server (Unix/Linux/Mac)")
        run_gunicorn()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
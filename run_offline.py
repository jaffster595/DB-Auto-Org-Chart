"""
Use this file instead of run_waitress.py if you want to skip the Graph API update. This file will 
launch the application using the last valid employee_data.json information.
"""

from waitress import serve
from app import app
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("=== OFFLINE MODE ACTIVE ===")
    logger.info("No Azure Graph API calls or auto-updates will occur.")
    logger.info("Serving existing employee_data.json file.")
    logger.info("Populate/update the JSON via CSV import script if needed.")
    logger.info("=============================")
    
    host = '0.0.0.0'
    port = 5000
    threads = 6  # Number of threads to handle requests
    
    logger.info(f"Starting Offline Waitress server on {host}:{port}")
    logger.info(f"Server running with {threads} threads")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        serve(
            app,
            host=host,
            port=port,
            threads=threads,
            url_scheme='http',
            ident='DB AutoOrgChart (Offline)',
            cleanup_interval=30,
            channel_timeout=120,
            connection_limit=100,
            asyncore_use_poll=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
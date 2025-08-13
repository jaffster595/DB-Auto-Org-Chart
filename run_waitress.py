"""
Waitress WSGI Server for Windows
This is a production-ready alternative to Gunicorn for Windows systems.
"""

from waitress import serve
from app import app, start_scheduler
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    start_scheduler()
    
    host = '0.0.0.0'
    port = 5000
    threads = 6  # Number of threads to handle requests
    
    logger.info(f"Starting Waitress server on {host}:{port}")
    logger.info(f"Server running with {threads} threads")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        serve(
            app,
            host=host,
            port=port,
            threads=threads,
            url_scheme='http',
            ident='DB AutoOrgChart',
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
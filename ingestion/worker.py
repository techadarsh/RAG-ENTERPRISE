"""
RQ Worker for asynchronous document ingestion
Consumes jobs from Redis queue and processes documents
"""
import logging
import sys
import os

# Add parent directory to path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from redis import Redis
from rq import Worker, Queue, Connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def run_worker():
    """
    Start RQ worker to consume jobs from the ingestion queue
    """
    logger.info(f" Starting RQ worker for ingestion queue...")
    logger.info(f" Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    
    with Connection(redis_conn):
        queue = Queue('ingestion', connection=redis_conn)
        worker = Worker([queue], connection=redis_conn)
        
        logger.info(f" Worker ready to process jobs from 'ingestion' queue")
        logger.info(f" Queue size: {len(queue)}")
        
        # Start consuming jobs
        worker.work(with_scheduler=True)

if __name__ == '__main__':
    try:
        run_worker()
    except KeyboardInterrupt:
        logger.info("⏹  Worker stopped by user")
    except Exception as e:
        logger.error(f" Worker error: {e}", exc_info=True)
        sys.exit(1)

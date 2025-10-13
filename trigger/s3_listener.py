"""
MinIO/S3 Event Listener Module - Auto-triggers ingestion for bucket uploads
Listens to bucket notifications and enqueues ingestion jobs to Redis queue
"""
import os
import time
import logging
from pathlib import Path
from typing import Optional
import json
from minio import Minio
from minio.notificationconfig import (
    NotificationConfig, QueueConfig, PrefixFilterRule
)
from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)


class MinIOEventListener:
    """
    Listens to MinIO bucket events and triggers ingestion for new objects
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.pdf', '.doc', '.docx'}
    
    def __init__(
        self,
        minio_endpoint: str,
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket_name: str = "documents",
        prefix: str = "incoming/",
        redis_host: str = "redis",
        redis_port: int = 6379,
        redis_db: int = 0,
        download_dir: str = "/app/data/s3_downloads"
    ):
        """
        Initialize MinIO event listener
        
        Args:
            minio_endpoint: MinIO server endpoint (e.g., 'minio:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket_name: Bucket to monitor
            prefix: Object prefix filter (e.g., 'incoming/')
            redis_host: Redis server hostname
            redis_port: Redis server port
            redis_db: Redis database number
            download_dir: Local directory for downloading files
        """
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.download_dir = download_dir
        
        # Ensure download directory exists
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize MinIO client
        # Parse endpoint to check if it includes http/https
        endpoint = minio_endpoint.replace('http://', '').replace('https://', '')
        secure = minio_endpoint.startswith('https://')
        
        self.minio_client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        logger.info(f" Connected to MinIO at {minio_endpoint}")
        
        # Create bucket if it doesn't exist
        try:
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
                logger.info(f" Created bucket: {bucket_name}")
            else:
                logger.info(f" Using existing bucket: {bucket_name}")
        except Exception as e:
            logger.error(f" Error checking/creating bucket: {e}")
            raise
        
        # Initialize Redis connection
        self.redis_conn = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        
        # Test Redis connection
        self.redis_conn.ping()
        logger.info(f" Connected to Redis at {redis_host}:{redis_port}")
        
        # Initialize RQ queue
        self.queue = Queue('ingestion', connection=self.redis_conn)
        
    def should_process_object(self, object_name: str) -> bool:
        """
        Check if object should be processed based on extension
        
        Args:
            object_name: Name of the object in bucket
            
        Returns:
            True if object should be processed, False otherwise
        """
        path = Path(object_name)
        
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"⏭  Ignoring unsupported file type: {object_name}")
            return False
        
        return True
    
    def download_and_enqueue(self, object_name: str):
        """
        Download object from MinIO and enqueue ingestion job
        
        Args:
            object_name: Name of the object in bucket
        """
        try:
            # Generate local file path
            local_filename = Path(object_name).name
            local_path = os.path.join(self.download_dir, local_filename)
            
            # Download file
            logger.info(f"  Downloading object: {object_name}")
            self.minio_client.fget_object(
                self.bucket_name,
                object_name,
                local_path
            )
            
            # Verify file was downloaded
            if not os.path.exists(local_path):
                logger.error(f" Downloaded file not found: {local_path}")
                return
            
            # Enqueue ingestion job
            job = self.queue.enqueue(
                'ingestion.pipeline.ingest_document_job',
                local_path,
                job_timeout='10m',
                result_ttl=86400,
                failure_ttl=604800
            )
            
            logger.info(
                f"  S3 event received: {object_name} → Downloaded → "
                f"Enqueued job {job.id}"
            )
            
        except Exception as e:
            logger.error(f" Error downloading/enqueuing object {object_name}: {e}")
    
    def listen_events(self):
        """
        Listen for bucket events using MinIO's listen_bucket_notification
        This uses long-polling to receive events
        """
        logger.info(f" Starting MinIO event listener for bucket: {self.bucket_name}")
        logger.info(f" Monitoring prefix: {self.prefix}")
        logger.info(f" Supported extensions: {', '.join(self.SUPPORTED_EXTENSIONS)}")
        
        try:
            # Listen for events (this blocks)
            events = self.minio_client.listen_bucket_notification(
                self.bucket_name,
                prefix=self.prefix,
                events=['s3:ObjectCreated:*']
            )
            
            for event in events:
                # Parse event
                try:
                    for record in event.get('Records', []):
                        object_name = record['s3']['object']['key']
                        event_name = record['eventName']
                        
                        logger.debug(f" Received event: {event_name} for {object_name}")
                        
                        # Check if we should process this object
                        if self.should_process_object(object_name):
                            self.download_and_enqueue(object_name)
                            
                except Exception as e:
                    logger.error(f" Error processing event: {e}")
                    
        except KeyboardInterrupt:
            logger.info(" Stopping MinIO event listener...")
        except Exception as e:
            logger.error(f" Error in event listener: {e}")
            raise
    
    def start(self):
        """Start listening for events"""
        self.listen_events()


def main():
    """Main entry point for standalone S3 listener"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get configuration from environment
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    bucket_name = os.getenv("S3_BUCKET_NAME", "documents")
    prefix = os.getenv("S3_WATCH_PREFIX", "incoming/")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    download_dir = os.getenv("S3_DOWNLOAD_DIR", "/app/data/s3_downloads")
    
    logger.info(" Initializing MinIO/S3 Event Listener Service")
    logger.info(f"   MinIO Endpoint: {minio_endpoint}")
    logger.info(f"   Bucket: {bucket_name}")
    logger.info(f"   Prefix: {prefix}")
    logger.info(f"   Redis: {redis_host}:{redis_port}/{redis_db}")
    
    # Create and start listener
    listener = MinIOEventListener(
        minio_endpoint=minio_endpoint,
        access_key=minio_access_key,
        secret_key=minio_secret_key,
        bucket_name=bucket_name,
        prefix=prefix,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
        download_dir=download_dir
    )
    
    listener.start()


if __name__ == "__main__":
    main()

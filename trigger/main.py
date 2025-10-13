"""
Trigger Service Main Orchestrator
Starts enabled trigger services based on configuration
"""
import os
import sys
import logging
import threading
import time
from typing import List

logger = logging.getLogger(__name__)


def start_folder_watcher():
    """Start folder watcher in a separate thread"""
    from watcher import FolderWatcher
    
    watch_dir = os.getenv("WATCH_DIR", "/app/data/incoming")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    
    logger.info(" Starting Folder Watcher...")
    watcher = FolderWatcher(
        watch_dir=watch_dir,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db
    )
    watcher.start()


def start_s3_listener():
    """Start S3/MinIO listener in a separate thread"""
    from s3_listener import MinIOEventListener
    
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    bucket_name = os.getenv("S3_BUCKET_NAME", "documents")
    prefix = os.getenv("S3_WATCH_PREFIX", "incoming/")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    download_dir = os.getenv("S3_DOWNLOAD_DIR", "/app/data/s3_downloads")
    
    logger.info("  Starting MinIO/S3 Event Listener...")
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


def main():
    """
    Main entry point for trigger service orchestrator
    Starts enabled trigger services based on environment configuration
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=" * 60)
    logger.info(" RAG Enterprise - Auto-Trigger Ingestion Service")
    logger.info("=" * 60)
    
    # Check which triggers are enabled
    enable_folder_watcher = os.getenv("ENABLE_FOLDER_WATCHER", "false").lower() == "true"
    enable_s3_trigger = os.getenv("ENABLE_S3_TRIGGER", "false").lower() == "true"
    
    if not enable_folder_watcher and not enable_s3_trigger:
        logger.warning("  No triggers enabled!")
        logger.warning("   Set ENABLE_FOLDER_WATCHER=true or ENABLE_S3_TRIGGER=true")
        logger.warning("   Exiting...")
        sys.exit(1)
    
    logger.info("\n Configuration:")
    logger.info(f"   Folder Watcher: {' Enabled' if enable_folder_watcher else ' Disabled'}")
    logger.info(f"   S3/MinIO Listener: {' Enabled' if enable_s3_trigger else ' Disabled'}")
    
    # Start enabled triggers in separate threads
    threads: List[threading.Thread] = []
    
    if enable_folder_watcher:
        folder_thread = threading.Thread(
            target=start_folder_watcher,
            name="FolderWatcher",
            daemon=True
        )
        folder_thread.start()
        threads.append(folder_thread)
        logger.info(" Folder Watcher thread started")
    
    if enable_s3_trigger:
        s3_thread = threading.Thread(
            target=start_s3_listener,
            name="S3Listener",
            daemon=True
        )
        s3_thread.start()
        threads.append(s3_thread)
        logger.info(" S3 Listener thread started")
    
    logger.info("\n" + "=" * 60)
    logger.info(" All enabled triggers are running!")
    logger.info("   Press Ctrl+C to stop all services")
    logger.info("=" * 60 + "\n")
    
    # Keep main thread alive and monitor child threads
    try:
        while True:
            time.sleep(1)
            
            # Check if any thread has died
            for thread in threads:
                if not thread.is_alive():
                    logger.error(f" Thread {thread.name} has died!")
                    logger.error("   Restarting may be required")
                    
    except KeyboardInterrupt:
        logger.info("\n Received shutdown signal...")
        logger.info("   Waiting for threads to stop...")
        
        # Give threads time to cleanup
        time.sleep(2)
        
        logger.info(" Trigger service stopped")


if __name__ == "__main__":
    main()

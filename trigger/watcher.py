"""
Folder Watcher Module - Auto-triggers ingestion for new files
Monitors a designated folder and enqueues ingestion jobs to Redis queue
"""
import os
import time
import logging
from pathlib import Path
from typing import Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)


class DocumentFileHandler(FileSystemEventHandler):
    """
    Handles file system events for document files
    Enqueues ingestion jobs when new documents are created or modified
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.pdf', '.doc', '.docx'}
    
    # Temporary file patterns to ignore
    IGNORE_PATTERNS = {'.tmp', '.swp', '~', '.DS_Store', '.lock'}
    
    def __init__(self, redis_queue: Queue, max_retries: int = 3):
        """
        Initialize the file handler
        
        Args:
            redis_queue: RQ Queue instance for job enqueuing
            max_retries: Maximum number of retry attempts for failed enqueue operations
        """
        super().__init__()
        self.queue = redis_queue
        self.max_retries = max_retries
        self.processing_files: Set[str] = set()  # Track files being processed
        
    def should_process_file(self, file_path: str) -> bool:
        """
        Check if file should be processed
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be processed, False otherwise
        """
        path = Path(file_path)
        
        # Check if it's a file (not directory)
        if not path.is_file():
            return False
        
        # Check extension
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"⏭️  Ignoring unsupported file type: {path.name}")
            return False
        
        # Check for temporary file patterns
        for pattern in self.IGNORE_PATTERNS:
            if pattern in path.name:
                logger.debug(f"⏭️  Ignoring temporary file: {path.name}")
                return False
        
        # Check if already processing
        if file_path in self.processing_files:
            logger.debug(f"⏭️  Already processing: {path.name}")
            return False
        
        return True
    
    def enqueue_ingestion_job(self, file_path: str, event_type: str):
        """
        Enqueue ingestion job to Redis queue with retry logic
        
        Args:
            file_path: Absolute path to the file
            event_type: Type of file system event (created/modified)
        """
        path = Path(file_path)
        
        # Mark as processing
        self.processing_files.add(file_path)
        
        try:
            # Wait a moment to ensure file write is complete
            time.sleep(0.5)
            
            # Verify file still exists and is readable
            if not path.exists():
                logger.warning(f"⚠️  File disappeared before enqueuing: {path.name}")
                return
            
            if not os.access(file_path, os.R_OK):
                logger.warning(f"⚠️  File not readable: {path.name}")
                return
            
            # Enqueue job with retries
            for attempt in range(1, self.max_retries + 1):
                try:
                    job = self.queue.enqueue(
                        'ingestion.pipeline.ingest_document_job',
                        file_path,
                        job_timeout='10m',
                        result_ttl=86400,  # Keep results for 24 hours
                        failure_ttl=604800  # Keep failed jobs for 7 days
                    )
                    
                    logger.info(
                        f"📂 New file detected ({event_type}): {path.name} "
                        f"→ Enqueued job {job.id}"
                    )
                    break
                    
                except Exception as e:
                    if attempt < self.max_retries:
                        logger.warning(
                            f"⚠️  Failed to enqueue job (attempt {attempt}/{self.max_retries}): {e}"
                        )
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        logger.error(
                            f"❌ Failed to enqueue job after {self.max_retries} attempts: {e}"
                        )
                        raise
                        
        except Exception as e:
            logger.error(f"❌ Error processing file {path.name}: {e}")
        finally:
            # Remove from processing set
            self.processing_files.discard(file_path)
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events"""
        if not event.is_directory and self.should_process_file(event.src_path):
            self.enqueue_ingestion_job(event.src_path, "created")
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events"""
        if not event.is_directory and self.should_process_file(event.src_path):
            self.enqueue_ingestion_job(event.src_path, "modified")


class FolderWatcher:
    """
    Monitors a folder for new/modified documents and triggers ingestion
    """
    
    def __init__(
        self,
        watch_dir: str,
        redis_host: str = "redis",
        redis_port: int = 6379,
        redis_db: int = 0
    ):
        """
        Initialize the folder watcher
        
        Args:
            watch_dir: Directory to monitor
            redis_host: Redis server hostname
            redis_port: Redis server port
            redis_db: Redis database number
        """
        self.watch_dir = watch_dir
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        
        # Ensure watch directory exists
        Path(watch_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize Redis connection
        self.redis_conn = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        
        # Test Redis connection
        self.redis_conn.ping()
        logger.info(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        
        # Initialize RQ queue
        self.queue = Queue('ingestion', connection=self.redis_conn)
        
        # Initialize file handler and observer
        self.event_handler = DocumentFileHandler(self.queue)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.watch_dir, recursive=True)
        
    def start(self):
        """Start monitoring the folder"""
        logger.info(f"👀 Starting folder watcher for: {self.watch_dir}")
        logger.info(f"📋 Supported extensions: {', '.join(DocumentFileHandler.SUPPORTED_EXTENSIONS)}")
        
        self.observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Stopping folder watcher...")
            self.stop()
    
    def stop(self):
        """Stop monitoring the folder"""
        self.observer.stop()
        self.observer.join()
        logger.info("✅ Folder watcher stopped")


def main():
    """Main entry point for standalone folder watcher"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get configuration from environment
    watch_dir = os.getenv("WATCH_DIR", "/app/data/incoming")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    
    logger.info("🚀 Initializing Folder Watcher Service")
    logger.info(f"   Watch Directory: {watch_dir}")
    logger.info(f"   Redis: {redis_host}:{redis_port}/{redis_db}")
    
    # Create and start watcher
    watcher = FolderWatcher(
        watch_dir=watch_dir,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db
    )
    
    watcher.start()


if __name__ == "__main__":
    main()

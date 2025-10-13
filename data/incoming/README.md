# Auto-Trigger Ingestion

Drop files here (.txt, .md, .pdf, .doc, .docx) to automatically trigger ingestion when folder watcher is enabled.

To enable:
1. Set ENABLE_FOLDER_WATCHER=true in .env
2. Start trigger service: docker compose --profile trigger up -d

Files placed here will be automatically detected and queued for processing.

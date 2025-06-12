# scripts/backup.py
import os
import shutil
import tarfile
from datetime import datetime
import boto3  # For S3 backup

class BackupManager:
    def __init__(self, config):
        self.config = config
        self.s3_client = boto3.client('s3') if config.get('use_s3') else None
        
    def backup_database(self):
        """Backup database with rotation"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"backup_db_{timestamp}.sql"
        
        # PostgreSQL backup
        os.system(f"pg_dump {self.config['db_name']} > {backup_file}")
        
        # Compress
        with tarfile.open(f"{backup_file}.tar.gz", "w:gz") as tar:
            tar.add(backup_file)
        
        # Upload to S3 if configured
        if self.s3_client:
            self.s3_client.upload_file(
                f"{backup_file}.tar.gz",
                self.config['s3_bucket'],
                f"backups/{backup_file}.tar.gz"
            )
        
        # Rotate old backups (keep last 7 days)
        self._rotate_backups()
    
    def backup_models(self):
        """Backup ML models with versioning"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_backup = f"models_backup_{timestamp}"
        shutil.copytree("models", model_backup)
        
        # Create model registry
        self._update_model_registry(timestamp)

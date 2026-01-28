"""
Backup management utilities for MShift.

Provides functionality to create and manage backup files with rotation.
"""
import os
import shutil
from datetime import datetime
from typing import Optional


def create_backup(file_path: str, max_backups: int = 5) -> Optional[str]:
    """
    Create a backup of the specified file with timestamp.
    
    Args:
        file_path: Path to the file to backup
        max_backups: Maximum number of backup files to keep (default: 5)
    
    Returns:
        Path to the created backup file, or None if backup failed
    """
    if not os.path.exists(file_path):
        return None
    
    # Create backup directory if it doesn't exist
    backup_dir = os.path.join(os.path.dirname(file_path), ".mshift_backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename with timestamp
    base_name = os.path.basename(file_path)
    name_without_ext, ext = os.path.splitext(base_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{name_without_ext}_backup_{timestamp}{ext}"
    backup_path = os.path.join(backup_dir, backup_name)
    
    try:
        # Create the backup
        shutil.copy2(file_path, backup_path)
        
        # Rotate old backups
        rotate_backups(backup_dir, base_name, max_backups)
        
        return backup_path
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None


def rotate_backups(backup_dir: str, original_filename: str, max_backups: int):
    """
    Remove old backup files, keeping only the most recent max_backups files.
    
    Args:
        backup_dir: Directory containing backup files
        original_filename: Original filename (without path) to match backups for
        max_backups: Maximum number of backups to keep
    """
    if not os.path.exists(backup_dir):
        return
    
    # Get all backup files for this original file
    name_without_ext, ext = os.path.splitext(original_filename)
    backup_prefix = f"{name_without_ext}_backup_"
    
    backup_files = []
    for filename in os.listdir(backup_dir):
        if filename.startswith(backup_prefix) and filename.endswith(ext):
            full_path = os.path.join(backup_dir, filename)
            if os.path.isfile(full_path):
                backup_files.append((full_path, os.path.getmtime(full_path)))
    
    # Sort by modification time (newest first)
    backup_files.sort(key=lambda x: x[1], reverse=True)
    
    # Remove old backups beyond max_backups
    for backup_path, _ in backup_files[max_backups:]:
        try:
            os.remove(backup_path)
            print(f"Removed old backup: {os.path.basename(backup_path)}")
        except Exception as e:
            print(f"Error removing old backup {backup_path}: {e}")


def get_backup_list(file_path: str) -> list[tuple[str, datetime]]:
    """
    Get a list of available backups for a file.
    
    Args:
        file_path: Path to the original file
    
    Returns:
        List of tuples (backup_path, modification_datetime) sorted by date (newest first)
    """
    backup_dir = os.path.join(os.path.dirname(file_path), ".mshift_backups")
    if not os.path.exists(backup_dir):
        return []
    
    base_name = os.path.basename(file_path)
    name_without_ext, ext = os.path.splitext(base_name)
    backup_prefix = f"{name_without_ext}_backup_"
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.startswith(backup_prefix) and filename.endswith(ext):
            full_path = os.path.join(backup_dir, filename)
            if os.path.isfile(full_path):
                mtime = os.path.getmtime(full_path)
                backups.append((full_path, datetime.fromtimestamp(mtime)))
    
    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x[1], reverse=True)
    
    return backups


def restore_from_backup(backup_path: str, target_path: str) -> bool:
    """
    Restore a file from a backup.
    
    Args:
        backup_path: Path to the backup file
        target_path: Path where the file should be restored
    
    Returns:
        True if restoration was successful, False otherwise
    """
    try:
        # Create a backup of the current file before restoring
        if os.path.exists(target_path):
            create_backup(target_path)
        
        # Restore the backup
        shutil.copy2(backup_path, target_path)
        return True
    except Exception as e:
        print(f"Error restoring from backup: {e}")
        return False

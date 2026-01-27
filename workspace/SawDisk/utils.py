"""
Utility functions for SawDisk
"""
import os
import stat
from pathlib import Path


def format_file_size(size_bytes: int, use_decimal: bool = True) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        use_decimal: If True, use decimal units (1000-based) like macOS.
                     If False, use binary units (1024-based) like traditional Linux.
    """
    if use_decimal:
        # Decimal units (macOS style): 1 KB = 1000 bytes, 1 GB = 1,000,000,000 bytes
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        divisor = 1000.0
    else:
        # Binary units (traditional): 1 KB = 1024 bytes, 1 GB = 1,073,741,824 bytes
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        divisor = 1024.0
    
    size = float(size_bytes)
    for unit in units:
        if size < divisor:
            return f"{size:.1f} {unit}"
        size /= divisor
    return f"{size:.1f} {units[-1]}"


def is_binary_file(file_path: str, chunk_size: int = 1024) -> bool:
    """Simple check if file is binary"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
            # If chunk contains null bytes, likely binary
            if b'\0' in chunk:
                return True
            # Check for common binary patterns
            if chunk[0:2] in [b'\x89PNG', b'\xff\xd8\xff', b'\x50\x4b']:
                return True
            return False
    except Exception:
        return False


def format_confidence(confidence: float) -> str:
    """Format confidence score with appropriate emoji"""
    if confidence >= 0.8:
        return f"🔴 High ({confidence:.1%})"
    elif confidence >= 0.5:
        return f"🟡 Medium ({confidence:.1%})"
    else:
        return f"🟢 Low ({confidence:.1%})"


def validate_path(path: str) -> bool:
    """Validate if path exists and is accessible"""
    try:
        path_obj = Path(path)
        return path_obj.exists() and path_obj.is_dir()
    except Exception:
        return False


def get_file_permissions(file_path: str) -> str:
    """Get file permissions as string"""
    try:
        stat_info = os.stat(file_path)
        permissions = stat.filemode(stat_info.st_mode)
        return permissions
    except Exception:
        return "unknown"


def sanitize_path(path: str) -> str:
    """Sanitize path for display (hide absolute paths in reports)"""
    # Replace common home directory paths with ~
    home_path = os.path.expanduser("~")
    if path.startswith(home_path):
        return path.replace(home_path, "~")
    return path

"""
Data models for SawDisk
"""
import time
import os
from typing import Dict, Any


class ScanResult:
    """Represents a detected crypto-related item"""
    
    def __init__(self, file_path: str, item_type: str, confidence: float, 
                 details: Dict[str, Any] = None):
        self.file_path = file_path
        self.item_type = item_type  # wallet, private_key, seed_phrase, etc.
        self.confidence = confidence
        self.details = details or {}
        self.scan_time = time.time()
        self.file_size = 0
        if os.path.exists(file_path):
            self.file_size = os.path.getsize(file_path)

"""
Scan History Management for SawDisk
Handles storage and retrieval of individual scan reports
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class ScanRecord:
    """Individual scan record"""
    scan_id: str
    timestamp: str
    drive_name: str
    scan_path: str
    files_found: int
    total_files_scanned: int
    scan_duration: float
    drive_size: str
    report_files: Dict[str, str]  # format -> file path
    status: str  # 'completed', 'running', 'failed'


class ScanHistoryManager:
    """Manages scan history and report storage"""
    
    def __init__(self, data_dir: str = "/app/data/scans"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "scan_history.json"
        self._load_history()
    
    def _load_history(self):
        """Load scan history from disk"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.scans = {scan['scan_id']: ScanRecord(**scan) for scan in data.get('scans', [])}
            else:
                self.scans = {}
        except Exception as e:
            print(f"⚠️  Error loading scan history: {e}")
            self.scans = {}
    
    def save_scan(self, scan_record: ScanRecord):
        """Save a scan record"""
        self.scans[scan_record.scan_id] = scan_record
        self._save_history()
    
    def _save_history(self):
        """Write scan history to disk"""
        try:
            data = {'scans': [asdict(scan) for scan in self.scans.values()]}
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)
        except Exception as e:
            print(f"⚠️  Error saving scan history: {e}")
    
    def get_scan(self, scan_id: str) -> Optional[ScanRecord]:
        """Get specific scan record"""
        return self.scans.get(scan_id)
    
    def get_all_scans(self) -> List[ScanRecord]:
        """Get all scan records, sorted by timestamp (newest first)"""
        return sorted(self.scans.values(), key=lambda x: x.timestamp, reverse=True)
    
    def get_scans_for_drive(self, drive_path: str) -> List[ScanRecord]:
        """Get all scans for a specific drive"""
        return [scan for scan in self.scans.values() if scan.scan_path == drive_path]
    
    def create_scan_directory(self, scan_id: str) -> Path:
        """Create directory for storing this scan's reports"""
        scan_dir = self.data_dir / scan_id
        scan_dir.mkdir(exist_ok=True)
        return scan_dir
    
    def cleanup_old_scans(self, max_scans: int = 50):
        """Keep only the most recent scans"""
        scans_list = self.get_all_scans()
        if len(scans_list) > max_scans:
            scans_to_remove = scans_list[max_scans:]
            for scan in scans_to_remove:
                # Remove scan data if it exists
                scan_dir = self.data_dir / scan.scan_id
                if scan_dir.exists():
                    import shutil
                    shutil.rmtree(scan_dir)
                
                # Remove from history
                del self.scans[scan.scan_id]
            
            self._save_history()
            print(f"🧹 Cleaned up {len(scans_to_remove)} old scans")

"""
Core scanning functionality for SawDisk
"""
import os
import re
import threading
import time
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from config import Config
from models import ScanResult


class DiskScanner:
    """Main disk scanner class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.results = []
        self.lock = threading.Lock()
        self.scan_id = self._generate_scan_id()
        self.scan_progress = {
            'scan_id': self.scan_id,
            'current_file': '',
            'files_scanned': 0,
            'files_found': 0,
            'current_directory': '',
            'estimated_total_files': 0,
            'start_time': None,
            'scan_stats': {
                'total_files_scanned': 0,
                'total_directories': 0,
                'total_bytes_scanned': 0,
                'file_types': {},
                'largest_file': {'size': 0, 'path': ''},
                'directories_scanned': [],
                'extensions_found': set(),
                'crypto_extensions': 0,
                'text_files': 0,
                'binary_files': 0,
                'scan_depth_reached': 0
            }
        }
        
    def scan(self) -> List[ScanResult]:
        """Main scan method"""
        self.scan_progress['start_time'] = time.time()
        print(f"🔍 Scanning path: {self.config.scan_path}")
        
        # Get all files to scan
        files_to_scan = self._collect_files()
        
        if not files_to_scan:
            print("⚠️  No files found to scan")
            return []
            
        print(f"📁 Found {len(files_to_scan)} files to scan")
        self.scan_progress['estimated_total_files'] = len(files_to_scan)
        
        # Scan files with progress bar
        with ThreadPoolExecutor(max_workers=self.config.num_threads) as executor:
            with tqdm(total=len(files_to_scan), desc="Scanning files") as pbar:
                futures = {
                    executor.submit(self._scan_file_with_progress, i, file_path, len(files_to_scan)): (i, pbar)
                    for i, file_path in enumerate(files_to_scan)
                }
                
                for future in as_completed(futures):
                    i, pbar = futures[future]
                    result = future.result()
                    pbar.update(1)
                    
                    self.scan_progress['files_scanned'] = i + 1
                    self.scan_progress['current_file'] = files_to_scan[i]
                    
                    if result:
                        with self.lock:
                            self.results.append(result)
                            self.scan_progress['files_found'] += 1
                            
                        if self.config.verbose:
                            print(f"✅ Found: {result.item_type} - {result.file_path}")
        
        print(f"🎯 Scan complete! Found {len(self.results)} crypto-related items")
        return self.results
    
    def get_progress_info(self) -> dict:
        """Get current scan progress"""
        if self.scan_progress['start_time'] is None:
            return self.scan_progress
            
        elapsed_time = time.time() - self.scan_progress['start_time']
        files_scanned = self.scan_progress['files_scanned']
        total_files = self.scan_progress['estimated_total_files']
        
        progress_data = self.scan_progress.copy()
        
        if total_files > 0:
            progress_data['progress_percent'] = (files_scanned / total_files) * 100
        else:
            progress_data['progress_percent'] = 0
            
        progress_data['elapsed_time'] = elapsed_time
        progress_data['files_per_second'] = files_scanned / elapsed_time if elapsed_time > 0 else 0
        
        if files_scanned > 0 and total_files > 0:
            remaining_files = total_files - files_scanned
            if progress_data['files_per_second'] > 0:
                progress_data['eta_seconds'] = remaining_files / progress_data['files_per_second']
            else:
                progress_data['eta_seconds'] = 0
        else:
            progress_data['eta_seconds'] = 0
            
        return progress_data
    
    def _collect_files(self) -> List[str]:
        """Collect all files to scan with detailed statistics"""
        files = []
        scan_path = Path(self.config.scan_path)
        
        if not scan_path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {self.config.scan_path}")
        
        print(f"📂 Collecting files (max depth: {self.config.max_depth})...")
        
        try:
            # Use os.walk instead of rglob to avoid permission issues
            import os
            
            for root, dirs, files_list in os.walk(str(scan_path)):
                # Skip problematic directories to avoid permission errors
                dirs[:] = [d for d in dirs if not (d.startswith('.') and d in ['.Spotlight-V100', '.Trashes', '.TemporaryItems'])]
                
                # Track directories
                rel_path = Path(root).relative_to(scan_path) if Path(root) != scan_path else Path('.')
                dir_depth = len(rel_path.parts) - 1 if rel_path != Path('.') else 0
                
                if dir_depth > 0:  # Don't count root directory
                    self.scan_progress['scan_stats']['total_directories'] += 1
                    self.scan_progress['scan_stats']['scan_depth_reached'] = max(
                        self.scan_progress['scan_stats']['scan_depth_reached'], 
                        dir_depth
                    )
                    self.scan_progress['scan_stats']['directories_scanned'].append(root)
                
                # Process files
                for filename in files_list:
                    file_path = os.path.join(root, filename)
                    entry = Path(file_path)
                    
                    try:
                        if entry.is_file() and not entry.is_symlink():
                            file_info = entry.stat()
                            file_size = file_info.st_size
                            
                            # Update statistics
                            self.scan_progress['scan_stats']['total_files_scanned'] += 1
                            self.scan_progress['scan_stats']['total_bytes_scanned'] += file_size
                            
                            # Track largest file
                            if file_size > self.scan_progress['scan_stats']['largest_file']['size']:
                                self.scan_progress['scan_stats']['largest_file'] = {
                                    'size': file_size,
                                    'path': file_path
                                }
                            
                            # Track file extensions
                            ext = entry.suffix.lower() or 'no_extension'
                            if ext not in self.scan_progress['scan_stats']['file_types']:
                                self.scan_progress['scan_stats']['file_types'][ext] = {'count': 0, 'bytes': 0}
                            self.scan_progress['scan_stats']['file_types'][ext]['count'] += 1
                            self.scan_progress['scan_stats']['file_types'][ext]['bytes'] += file_size
                            self.scan_progress['scan_stats']['extensions_found'].add(ext)
                            
                            # Categorize files
                            if self._is_crypto_related_file(entry):
                                self.scan_progress['scan_stats']['crypto_extensions'] += 1
                                
                            # Skip files that are too large for actual scanning
                            if file_size > self.config.max_file_size:
                                continue
                                
                            # Add files that should be scanned - be more inclusive
                            should_scan = (
                                self._is_crypto_related_file(entry) or 
                                self._has_crypto_pattern_in_name(entry) or
                                entry.suffix.lower() in self.config.crypto_content_extensions
                            )
                            
                            if should_scan:
                                # Also categorize files for statistics
                                if entry.suffix.lower() in ['.txt', '.json', '.csv', '.log', '.cfg', '.conf', '.ini']:
                                    self.scan_progress['scan_stats']['text_files'] += 1
                                else:
                                    self.scan_progress['scan_stats']['binary_files'] += 1
                                    
                                files.append(file_path)
                                
                    except (PermissionError, OSError, FileNotFoundError):
                        # Skip problematic files silently
                        continue
                        
        except PermissionError as e:
            print(f"⚠️  Permission denied accessing some directories: {e}")
        except Exception as e:
            print(f"⚠️  Error collecting files: {e}")
        
        print(f"📊 Collection complete:")
        print(f"   Found {self.scan_progress['scan_stats']['total_files_scanned']} files")
        print(f"   Scanned {self.scan_progress['scan_stats']['total_directories']} directories") 
        print(f"   Total size: {self._convert_bytes(self.scan_progress['scan_stats']['total_bytes_scanned'])}")
        print(f"   Files to analyze: {len(files)}")
        
        print(f"   Files under {self.config.max_file_size} limit: {len(files)}")
        print(f"   File types included: crypto extensions + {list(self.config.crypto_content_extensions)}")
            
        return files
    
    def _generate_scan_id(self) -> str:
        """Generate unique scan ID"""
        import time
        import os
        from datetime import datetime
        
        # Create ID from timestamp, drive name, and random component
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drive_name = Path(self.config.scan_path).name.replace('/', '_').replace(' ', '_')
        
        # Add small random component to ensure uniqueness even when scanning same drive quickly
        random_suffix = hex(int(time.time() * 1000000) % 10000)[2:].zfill(4)
        
        return f"scan_{timestamp}_{drive_name}_{random_suffix}"
    
    def _convert_bytes(self, bytes_value: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
    
    def get_scan_summary(self) -> dict:
        """Get comprehensive scan summary"""
        if self.scan_progress['start_time'] is None:
            return {'status': 'no_scan_run'}
            
        elapsed_time = time.time() - self.scan_progress['start_time']
        stats = self.scan_progress['scan_stats']
        
        # Convert extensions set to list for JSON serialization
        extensions_found = list(stats['extensions_found'])
        
        # Count crypto-related files
        crypto_file_count = sum(1 for ext, data in stats['file_types'].items()
                              if ext.lower() in self.config.crypto_extensions)
        
        # Top 10 file types by count
        top_file_types = sorted(stats['file_types'].items(), 
                              key=lambda x: x[1]['count'], reverse=True)[:10]
        
        summary = {
            'scan_status': 'completed',
            'scan_path': self.config.scan_path,
            'scan_duration': elapsed_time,
            'scan_summary': {
                'total_files_found': stats['total_files_scanned'],
                'total_directories_scanned': stats['total_directories'],
                'total_bytes_scanned': stats['total_bytes_scanned'],
                'total_bytes_scanned_readable': self._convert_bytes(stats['total_bytes_scanned']),
                'files_analyzed': self.scan_progress['files_scanned'],
                'crypto_items_found': len(self.results),
                'crypto_extensions_found': stats['crypto_extensions'],
                'scan_depth_reached': stats['scan_depth_reached'],
                'max_depth_configured': self.config.max_depth,
                'threads_used': self.config.num_threads,
                'scan_speed_files_per_second': self.scan_progress['files_scanned'] / elapsed_time if elapsed_time > 0 else 0,
                'scan_speed_mb_per_second': (stats['total_bytes_scanned'] / (1024*1024)) / elapsed_time if elapsed_time > 0 else 0
            },
            'file_statistics': {
                'unique_extensions_found': len(extensions_found),
                'total_extensions': extensions_found,
                'top_10_file_types': [{'extension': ext, 'count': data['count'], 'total_bytes': data['bytes']} 
                                    for ext, data in top_file_types],
                'largest_file': {
                    'size': stats['largest_file']['size'],
                    'size_readable': self._convert_bytes(stats['largest_file']['size']),
                    'path': stats['largest_file']['path']
                },
                'crypto_related_files': crypto_file_count
            },
            'scan_results': [
                {
                    'type': result.item_type,
                    'confidence': result.confidence,
                    'path': result.file_path,
                    'size': result.file_size,
                    'size_readable': self._convert_bytes(result.file_size)
                } for result in self.results
            ]
        }
        
        return summary
    
    def _is_crypto_related_file(self, file_path: Path) -> bool:
        """Check if file has crypto-related extension"""
        return file_path.suffix.lower() in self.config.crypto_extensions
    
    def _has_crypto_pattern_in_name(self, file_path: Path) -> bool:
        """Check if file name matches crypto patterns"""
        name = file_path.name.lower()
        
        for wallet_type, patterns in self.config.wallet_patterns.items():
            for pattern in patterns:
                if pattern.lower() in name:
                    return True
        return False
    
    def _scan_file(self, file_path: str) -> ScanResult:
        """Scan a single file for crypto-related content"""
        try:
            # Import here to avoid circular import
            from crypto_detector import CryptoDetector
            detector = CryptoDetector(self.config)
            return detector.analyze_file(file_path)
        except Exception as e:
            if self.config.verbose:
                print(f"⚠️  Error scanning {file_path}: {e}")
            return None
    
    def _scan_file_with_progress(self, index: int, file_path: str, total_files: int) -> ScanResult:
        """Scan a single file with progress tracking"""
        try:
            # Update current file path for progress tracking
            self.scan_progress['current_file'] = str(file_path)
            
            # Extract directory for progress display
            file_path_obj = Path(file_path)
            self.scan_progress['current_directory'] = str(file_path_obj.parent)
            
            # Scan the file
            from crypto_detector import CryptoDetector
            detector = CryptoDetector(self.config)
            result = detector.analyze_file(file_path)
            
            # Update progress
            self.scan_progress['files_scanned'] = index + 1
            
            return result
            
        except Exception as e:
            if self.config.verbose:
                print(f"⚠️  Error scanning {file_path}: {e}")
            
            # Still update progress even on error
            self.scan_progress['files_scanned'] = index + 1
            return None


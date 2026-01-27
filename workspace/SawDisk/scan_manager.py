"""
Scan Manager for SawDisk
Handles exclusive scan execution and real-time state management
"""

import threading
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from scanner import DiskScanner
from config import Config
from scan_history import ScanHistoryManager, ScanRecord


@dataclass
class ScanSession:
    """Active scan session"""
    scan_id: str
    thread: threading.Thread
    scanner: DiskScanner
    config: Config
    start_time: float
    status: str  # 'running', 'stopping', 'stopped', 'completed', 'error'
    stop_requested: bool = False
    results: list = None


class ScanManager:
    """Singleton scan manager ensuring only one scan runs at a time"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.current_session: Optional[ScanSession] = None
            self.session_lock = threading.RLock()
            self.scan_history = ScanHistoryManager()
            self._status_callbacks = []
            self._initialized = True
    
    def add_status_callback(self, callback):
        """Add callback function to receive status updates"""
        self._status_callbacks.append(callback)
    
    def _notify_status(self, update: Dict[str, Any]):
        """Notify all registered callbacks about status changes"""
        for callback in self._status_callbacks:
            try:
                callback(update)
            except Exception as e:
                print(f"Error in status callback: {e}")
    
    def is_scan_running(self) -> bool:
        """Check if a scan is currently running"""
        with self.session_lock:
            return (self.current_session is not None and 
                    self.current_session.status in ['running', 'stopping'] and
                    self.current_session.thread.is_alive())
    
    def start_scan(self, config_dict: dict) -> Dict[str, Any]:
        """Start a new scan (only if no other scan is running)"""
        with self.session_lock:
            if self.is_scan_running():
                return {
                    'error': 'Another scan is already running',
                    'current_scan_id': self.current_session.scan_id if self.current_session else None
                }
            
            # Create unique scan ID
            scan_id = self._generate_scan_id()
            
            # Create config
            config = Config(**config_dict)
            
            # Create scanner
            scanner = DiskScanner(config)
            scanner.scan_id = scan_id
            
            # Create scan session
            self.current_session = ScanSession(
                scan_id=scan_id,
                thread=None,
                scanner=scanner,
                config=config,
                start_time=time.time(),
                status='running',
                results=[]
            )
            
            # Start scan thread
            self.current_session.thread = threading.Thread(
                target=self._run_scan_thread,
                daemon=True
            )
            self.current_session.thread.start()
            
            # Create scan record
            scan_path_str = str(config.scan_path)
            scan_path_obj = Path(config.scan_path) if not isinstance(config.scan_path, Path) else config.scan_path
            scan_record = ScanRecord(
                scan_id=scan_id,
                timestamp=datetime.now().isoformat(),
                drive_name=scan_path_obj.name if hasattr(scan_path_obj, 'name') else Path(scan_path_str).name,
                scan_path=scan_path_str,
                files_found=0,
                total_files_scanned=0,
                scan_duration=0,
                drive_size="",
                report_files={},
                status='running'
            )
            self.scan_history.save_scan(scan_record)
            
            print(f"Started new scan: {scan_id}")
            print(f"Scanning: {config.scan_path}")
            
            return {
                'success': True,
                'scan_id': scan_id,
                'status': 'started',
                'message': 'Scan started successfully'
            }
    
    def stop_scan(self) -> Dict[str, Any]:
        """Stop the currently running scan"""
        with self.session_lock:
            if not self.is_scan_running():
                return {
                    'success': False,
                    'error': 'No scan is currently running'
                }
            
            print(f"Stopping scan: {self.current_session.scan_id}")
            self.current_session.stop_requested = True
            self.current_session.status = 'stopping'
            
            self._notify_status({
                'type': 'scan_control',
                'action': 'stopping',
                'scan_id': self.current_session.scan_id
            })
            
            return {
                'success': True,
                'status': 'stopping',
                'scan_id': self.current_session.scan_id,
                'message': 'Stop request sent'
            }
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current scan status with real-time info"""
        with self.session_lock:
            if not self.current_session:
                return {
                    'status': 'idle',
                    'is_running': False,
                    'message': 'No scan running'
                }
            
            session = self.current_session
            if session.status == 'running':
                try:
                    progress = session.scanner.get_progress_info()
                    scan_path_str = str(session.config.scan_path)
                    scan_path_obj = Path(session.config.scan_path) if not isinstance(session.config.scan_path, Path) else session.config.scan_path
                    drive_name = scan_path_obj.name if hasattr(scan_path_obj, 'name') else Path(scan_path_str).name
                    
                    return {
                        'status': 'running',
                        'is_running': True,
                        'scan_id': session.scan_id,
                        'drive': drive_name,
                        'scan_path': scan_path_str,
                        'progress': progress.get('progress_percent', 0),
                        'current_file': progress.get('current_file', ''),
                        'current_directory': progress.get('current_directory', ''),
                        'files_scanned': progress.get('files_scanned', 0),
                        'files_found': progress.get('files_found', 0),
                        'estimated_total_files': progress.get('estimated_total_files', 0),
                        'elapsed_time': progress.get('elapsed_time', 0),
                        'files_per_second': progress.get('files_per_second', 0),
                        'eta_seconds': progress.get('eta_seconds', 0),
                        'start_time': session.start_time,
                        'scan_stats': session.scanner.scan_progress.get('scan_stats', {}),
                        'results': session.results or [],
                        'stop_requested': session.stop_requested
                    }
                except Exception as e:
                    print(f"Error getting progress: {e}")
                    return {
                        'status': 'running',
                        'is_running': True,
                        'scan_id': session.scan_id,
                        'error': str(e)
                    }
            
            elif session.status == 'stopping':
                return {
                    'status': 'stopping',
                    'is_running': True,
                    'scan_id': session.scan_id,
                    'message': 'Stopping scan...'
                }
            
            else:
                return {
                    'status': session.status,
                    'is_running': False,
                    'scan_id': session.scan_id,
                    'results': session.results or [],
                    'scan_duration': time.time() - session.start_time
                }
    
    def _run_scan_thread(self):
        """Thread function to run the scan"""
        session = self.current_session
        try:
            print(f"Creating exclusive scan directory for: {session.scan_id}")
            
            # Create exclusive scan directory
            scan_dir = self.scan_history.create_scan_directory(session.scan_id)
            session.config.output_dir = str(scan_dir)
            
            # Start the scan
            session.scanner.config.output_dir = str(scan_dir)
            results = session.scanner.scan()
            
            # Update session with results
            session.results = [result.__dict__ for result in results]
            
            # Generate reports if scan completed successfully
            if not session.stop_requested:
                from reporter import ReportGenerator
                reporter = ReportGenerator(session.config)
                if session.results:
                    report_path = reporter.generate_report(results)
                    
                    # Calculate drive size
                    drive_size = "Unknown"
                    try:
                        import psutil
                        usage = psutil.disk_usage(session.config.scan_path)
                        drive_size = f"{usage.total / (1024**3):.1f} GB"
                    except:
                        pass
                    
                    # Update scan record with final results
                    scan_record = self.scan_history.get_scan(session.scan_id)
                    if scan_record:
                        scan_record.files_found = len(session.results)
                        scan_record.total_files_scanned = session.scanner.scan_progress['scan_stats']['total_files_scanned']
                        scan_record.scan_duration = time.time() - session.start_time
                        scan_record.drive_size = drive_size
                        scan_record.report_files = {'html': report_path} if report_path else {}
                        scan_record.status = 'completed'
                        self.scan_history.save_scan(scan_record)
                
                session.status = 'completed'
                print(f"Scan completed successfully: {session.scan_id}")
                
                self._notify_status({
                    'type': 'scan_complete',
                    'scan_id': session.scan_id,
                    'results_count': len(session.results),
                    'duration': time.time() - session.start_time
                })
            else:
                session.status = 'stopped'
                print(f"Scan stopped: {session.scan_id}")
                
        except Exception as e:
            session.status = 'error'
            print(f"Scan failed: {session.scan_id} - {e}")
            
            # Update scan record with error
            scan_record = self.scan_history.get_scan(session.scan_id)
            if scan_record:
                scan_record.status = 'failed'
                self.scan_history.save_scan(scan_record)
        
        finally:
            with self.session_lock:
                self.current_session = None
    
    def _generate_scan_id(self) -> str:
        """Generate unique scan ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = uuid.uuid4().hex[:8]
        return f"scan_{timestamp}_{random_suffix}"
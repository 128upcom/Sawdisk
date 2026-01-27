#!/usr/bin/env python3
"""
SawDisk Web Interface
A modern web-based dashboard for the SawDisk crypto scanner.
"""

import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import psutil

import sys
sys.path.append('/app/workspace/SawDisk')

from scanner import DiskScanner
from reporter import ReportGenerator
from config import Config
from scan_history import ScanHistoryManager, ScanRecord
from scan_manager import ScanManager
from utils import format_file_size, format_confidence

# Initialize Flask app
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
CORS(app)

# Global variables for scan status
scan_status = {
    'is_running': False,
    'progress': 0,
    'current_file': '',
    'results': [],
    'start_time': None,
    'errors': []
}

# Global scan manager (replaces individual scanner)
scan_manager = ScanManager()

# Legacy variable for compatibility
scan_history = scan_manager.scan_history

# Global scanner reference (for legacy compatibility)
current_scanner = None

def run_scan_async(config_dict):
    """Run scan in background thread"""
    global scan_status, scan_history
    
    try:
        scan_status['is_running'] = True
        scan_status['start_time'] = time.time()
        scan_status['progress'] = 0
        scan_status['current_file'] = 'Initializing...'
        scan_status['errors'] = []
        
        # Create config object
        config = Config(**config_dict)
        
        # Initialize scanner (this generates unique scan_id)
        scanner = DiskScanner(config)
        global current_scanner
        current_scanner = scanner
        
        # Create exclusive scan directory
        scan_dir = scan_history.create_scan_directory(scanner.scan_id)
        config.output_dir = str(scan_dir)
        
        # Create initial scan record
        scan_record = ScanRecord(
            scan_id=scanner.scan_id,
            timestamp=datetime.now().isoformat(),
            drive_name=Path(scanner.config.scan_path).name,
            scan_path=str(scanner.config.scan_path),
            files_found=0,
            total_files_scanned=0,
            scan_duration=0,
            drive_size="",
            report_files={},
            status='running'
        )
        scan_history.save_scan(scan_record)
        
        # Update scan status with scan_id
        scan_status['scan_id'] = scanner.scan_id
        scan_status['current_file'] = f"Scanning {config.scan_path}..."
        
        print(f"📁 Created exclusive scan directory: {scan_dir}")
        print(f"🔍 Scan ID: {scanner.scan_id}")
        
        # Start scanning
        results = scanner.scan()
        
        # Store results
        scan_status['results'] = [
            {
                'file_path': r.file_path,
                'item_type': r.item_type,
                'confidence': r.confidence,
                'file_size': r.file_size,
                'scan_time': r.scan_time,
                'details': r.details
            }
            for r in results
        ]
        
        # Generate report in exclusive directory
        if results:
            reporter = ReportGenerator(config)
            report_path = reporter.generate_report(results)
            scan_status['report_path'] = report_path
            
            # Update scan record with final results
            scan_record.files_found = len(results)
            scan_record.total_files_scanned = scanner.scan_progress['scan_stats']['total_files_scanned']
            scan_record.scan_duration = time.time() - scan_status['start_time']
            scan_record.report_files = {'html': report_path} if report_path else {}
            scan_record.status = 'completed'
            
            # Calculate drive size
            try:
                usage = psutil.disk_usage(config.scan_path)
                scan_record.drive_size = f"{usage.total / (1024**3):.1f} GB"
            except:
                scan_record.drive_size = "Unknown"
                
            scan_history.save_scan(scan_record)
        
        scan_status['progress'] = 100
        scan_status['current_file'] = 'Scan completed!'
        
    except Exception as e:
        scan_status['errors'].append(str(e))
        scan_status['current_file'] = f'Error: {str(e)}'
    finally:
        scan_status['is_running'] = False

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/scan')
def scan_page():
    """Scan configuration page"""
    return render_template('scan.html')

@app.route('/summary')
def summary_page():
    """Scan summary page"""
    return render_template('summary.html')

# Cache for system info to reduce expensive operations
_system_info_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 10  # Cache for 10 seconds
}

@app.route('/api/system-info')
def system_info():
    """Get system information (with caching to improve performance)"""
    global _system_info_cache
    
    # Return cached data if still valid
    current_time = time.time()
    if (_system_info_cache['data'] and 
        current_time - _system_info_cache['timestamp'] < _system_info_cache['ttl']):
        return jsonify(_system_info_cache['data'])
    
    mounts = []
    seen_mountpoints = set()  # Track to avoid duplicates
    
    # Check all partitions (limit to avoid blocking)
    try:
        partitions = psutil.disk_partitions()
        for partition in partitions[:50]:  # Limit to first 50 partitions
            try:
                mount_point = partition.mountpoint
                
                # Skip system directories and special mounts
                if (mount_point in ['/', '/proc', '/sys', '/dev', '/run', '/tmp'] or
                    mount_point.startswith('/etc/') or
                    mount_point.startswith('/dev/') or
                    mount_point.startswith('/var/') or
                    mount_point.startswith('/app/') or  # Skip Docker bind mounts
                    mount_point.startswith('/run/') or  # Skip Docker runtime mounts
                    '/oldroot' in mount_point or  # Skip Docker internal mounts
                    '/var/lib' in mount_point or  # Skip Docker internal mounts
                    mount_point in seen_mountpoints):
                    continue
                
                # Only include mount points that look like actual volumes
                # Skip if it's a file (like /etc/resolv.conf bind mount)
                if not os.path.isdir(mount_point):
                    continue
                
                usage = psutil.disk_usage(mount_point)
                seen_mountpoints.add(mount_point)
                
                mounts.append({
                    'device': partition.device,
                    'mountpoint': mount_point,
                    'fstype': partition.fstype,
                    'total': format_file_size(usage.total, use_decimal=True),
                    'used': format_file_size(usage.used, use_decimal=True),
                    'free': format_file_size(usage.free, use_decimal=True),
                    'percent': usage.percent
                })
            except (PermissionError, OSError, FileNotFoundError):
                continue
    except Exception as e:
        print(f"Error getting partitions: {e}")
    
    # Check /mnt/users (macOS Users directory, typically on system drive)
    users_path = '/mnt/users'
    if os.path.exists(users_path) and os.path.isdir(users_path):
        try:
            usage = psutil.disk_usage(users_path)
            # macOS system drive should be around 233-265 GB
            # Filter out Docker VM internal mounts (too small or too large)
            if 50 * 1024**3 < usage.total < 500 * 1024**3:  # Between 50GB and 500GB
                mounts.append({
                    'device': 'macOS System',
                    'mountpoint': users_path,
                    'fstype': 'apfs',
                    'total': format_file_size(usage.total, use_decimal=True),
                    'used': format_file_size(usage.used, use_decimal=True),
                    'free': format_file_size(usage.free, use_decimal=True),
                    'percent': usage.percent
                })
                seen_mountpoints.add(users_path)
        except (PermissionError, OSError, FileNotFoundError) as e:
            print(f"Error reading system drive: {e}")
    
    # Check /mnt/volumes (main target directory)
    # Note: Docker mounts /Volumes as a single mount point, so psutil.disk_usage() on subdirs
    # returns the parent mount size. We'll list volumes but note they're subdirectories.
    volumes_path = '/mnt/volumes'
    if os.path.exists(volumes_path):
        try:
            # Get the parent mount info first
            parent_usage = psutil.disk_usage(volumes_path)
            items = os.listdir(volumes_path)
            
            for item in items[:20]:  # Limit to first 20 items
                if item == 'PoC' or item.startswith('.'):
                    continue
                    
                item_path = os.path.join(volumes_path, item)
                
                # Handle symlinks - check if they point to valid volumes
                if os.path.islink(item_path):
                    real_path = os.path.realpath(item_path)
                    # Skip symlinks pointing to /, /proc, /sys, etc.
                    if real_path in ['/', '/proc', '/sys', '/dev'] or real_path.startswith('/proc') or real_path.startswith('/sys'):
                        print(f"Skipping invalid symlink {item} -> {real_path}")
                        continue
                    # If symlink points to a valid directory that's not root, use it
                    if os.path.isdir(real_path) and real_path != item_path and real_path != '/':
                        print(f"Following symlink {item} -> {real_path}")
                        item_path = real_path
                    # If symlink points to root or invalid location, skip
                    elif real_path == '/' or real_path == item_path or not os.path.exists(real_path):
                        print(f"Skipping broken/invalid symlink {item} -> {real_path}")
                        continue
                
                # Only process actual directories
                if os.path.isdir(item_path) and item_path not in seen_mountpoints:
                    try:
                        # Try to get disk usage - but note this may return parent mount size
                        usage = psutil.disk_usage(item_path)
                        
                        # If the size matches the parent mount exactly, it's likely a subdirectory
                        # not a separate mount. We'll still show it but note it's approximate.
                        # For Docker Desktop mounts, individual volumes appear as subdirectories
                        # of the parent /Volumes mount, so we can't get exact sizes.
                        
                        # Skip if this looks like the container root filesystem
                        if usage.total > 2 * 1024**4:  # > 2TB is suspicious
                            if not item_path.startswith('/mnt/volumes/'):
                                continue
                        
                        seen_mountpoints.add(item_path)
                        
                        # Note: For Docker Desktop, volumes mounted under /Volumes appear
                        # as subdirectories, so disk_usage() returns the parent mount size.
                        # We show it but the size may not be accurate for individual volumes.
                        mounts.append({
                            'device': f'Volume-{item}',
                            'mountpoint': item_path,
                            'fstype': 'external_drive',
                            'total': format_file_size(usage.total, use_decimal=True),
                            'used': format_file_size(usage.used, use_decimal=True),
                            'free': format_file_size(usage.free, use_decimal=True),
                            'percent': usage.percent,
                            'note': 'Size may reflect parent mount' if usage.total == parent_usage.total else None
                        })
                    except (PermissionError, OSError, FileNotFoundError) as e:
                        print(f"Skipping {item_path}: {e}")
                        continue
        except (OSError, PermissionError) as e:
            print(f"Error reading volumes: {e}")
    
    memory = psutil.virtual_memory()
    
    result = {
        'mounts': mounts,
        'memory': {
            'total': format_file_size(memory.total, use_decimal=True),
            'available': format_file_size(memory.available, use_decimal=True),
            'percent': memory.percent
        },
        'current_time': datetime.now().isoformat()
    }
    
    # Update cache
    _system_info_cache['data'] = result
    _system_info_cache['timestamp'] = current_time
    
    return jsonify(result)

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """Start a new scan (only one allowed at a time)"""
    global scan_manager
    
    data = request.get_json()
    
    # Default values
    config_dict = {
        'scan_path': data.get('scan_path', '/mnt/volumes'),
        'output_dir': data.get('output_dir', '/app/data/sawdisk_reports'),
        'report_format': data.get('report_format', 'html'),
        'max_depth': data.get('max_depth', 20),
        'num_threads': data.get('threads', 4),
        'verbose': data.get('verbose', False)
    }
    
    # Validate scan path
    if not os.path.exists(config_dict['scan_path']):
        return jsonify({'error': f"Scan path does not exist: {config_dict['scan_path']}"}), 400
    
    # Start scan using scan manager (handles exclusive execution)
    result = scan_manager.start_scan(config_dict)
    
    if 'error' in result:
        return jsonify({'error': result['error']}), 400
    
    return jsonify(result)

@app.route('/api/scan/status')
def scan_status_api():
    """Get current scan status with real-time info"""
    global scan_manager
    
    # Get real-time status from scan manager
    status = scan_manager.get_current_status()
    
    return jsonify(status)


@app.route('/api/scan/stop', methods=['POST'])
def stop_scan():
    """Stop the currently running scan"""
    global scan_manager
    
    result = scan_manager.stop_scan()
    
    if 'error' in result:
        return jsonify({'error': result['error']}), 400
    
    return jsonify(result)


@app.route('/api/results')
def get_results():
    """Get scan results"""
    return jsonify({
        'results': scan_status['results'],
        'total_found': len(scan_status['results']),
        'scan_time': scan_status['start_time'],
        'report_path': scan_status.get('report_path', '')
    })

@app.route('/api/scan/summary')
def get_scan_summary():
    """Get comprehensive scan summary with detailed statistics"""
    global scan_manager
    
    # Get current session from scan manager
    if not scan_manager.current_session or not scan_manager.current_session.scanner:
        return jsonify({'error': 'No scan has been performed yet'}), 404
    
    try:
        scanner = scan_manager.current_session.scanner
        summary = scanner.get_scan_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': f'Failed to generate summary: {str(e)}'}), 500


@app.route('/api/scan/history')
def scan_history_api():
    """Get scan history"""
    global scan_history
    try:
        scans = scan_history.get_all_scans()
        return jsonify({
            'scans': [
                {
                    'scan_id': scan.scan_id,
                    'timestamp': scan.timestamp,
                    'drive_name': scan.drive_name,
                    'scan_path': scan.scan_path,
                    'files_found': scan.files_found,
                    'total_files_scanned': scan.total_files_scanned,
                    'scan_duration': scan.scan_duration,
                    'drive_size': scan.drive_size,
                    'status': scan.status,
                    'report_files': scan.report_files
                }
                for scan in scans
            ],
            'total_scans': len(scans)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scan/<scan_id>')
def get_scan_report(scan_id):
    """Get specific scan report"""
    global scan_history
    try:
        scan_record = scan_history.get_scan(scan_id)
        if not scan_record:
            return jsonify({'error': 'Scan not found'}), 404
            
        return jsonify({
            'scan_id': scan_record.scan_id,
            'timestamp': scan_record.timestamp,
            'drive_name': scan_record.drive_name,
            'scan_path': scan_record.scan_path,
            'files_found': scan_record.files_found,
            'total_files_scanned': scan_record.total_files_scanned,
            'scan_duration': scan_record.scan_duration,
            'drive_size': scan_record.drive_size,
            'status': scan_record.status,
            'report_files': scan_record.report_files
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/browse')
def browse_files():
    """Browse directory structure"""
    path = request.args.get('path', '/mnt/volumes')
    
    if not os.path.exists(path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    try:
        items = []
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                try:
                    # Count files in directory (limit for performance)
                    file_count = 0
                    for _, _, files in os.walk(item_path):
                        file_count += len(files)
                        if file_count > 1000:  # Limit counting
                            break
                    
                    items.append({
                        'name': item,
                        'path': item_path,
                        'type': 'directory',
                        'file_count': file_count
                    })
                except PermissionError:
                    items.append({
                        'name': item,
                        'path': item_path,
                        'type': 'directory',
                        'file_count': 'N/A'
                    })
        
        return jsonify({
            'path': path,
            'items': items
        })
    
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403

@app.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve generated reports"""
    reports_dir = Path('/app/data/sawdisk_reports')
    report_path = reports_dir / filename
    
    if report_path.exists():
        from flask import send_file
        return send_file(report_path)
    else:
        return jsonify({'error': 'Report not found'}), 404

if __name__ == '__main__':
    # Create necessary directories
    Path('/app/data/sawdisk_reports').mkdir(parents=True, exist_ok=True)
    Path('workspace/SawDisk/templates').mkdir(parents=True, exist_ok=True)
    Path('workspace/SawDisk/static/css').mkdir(parents=True, exist_ok=True)
    Path('workspace/SawDisk/static/js').mkdir(parents=True, exist_ok=True)
    
    print("🌐 Starting SawDisk Web Interface...")
    print("📊 Dashboard: http://localhost:5000")
    print("🔍 Scan Interface: http://localhost:5000/scan")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

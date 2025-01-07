import socket
import json
import threading
import signal
import sys
from .tool_server import ToolServer
import http.server
import socketserver

class TestServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.tool_server = ToolServer()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True
        self.clients = []
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        print("\n[!] Shutting down server...")
        self.running = False
        for client in self.clients:
            try:
                client.send(json.dumps("quit").encode())
                client.close()
            except: pass
        self.sock.close()
        sys.exit(0)

    def handle_client(self, client_socket, addr):
        self.clients.append(client_socket)
        print(f"[+] Client {addr} connected")
        
        while self.running:
            try:
                command = input(f"[{addr[0]}:{addr[1]}]> ")
                if not command: continue
                
                client_socket.send(json.dumps(command).encode())
                client_socket.settimeout(5)
                response = client_socket.recv(4096).decode()
                
                try:
                    response = json.loads(response)
                    print(f"\nResponse from {addr[0]}:{addr[1]}:")
                    print("-" * 50)
                    print(response)
                    print("-" * 50)
                except:
                    print(f"Raw response: {response}")
                
                if command == 'quit': break
                    
            except socket.timeout:
                print("[!] Response timeout")
            except Exception as e:
                print(f"[!] Error: {e}")
                break
        
        self.clients.remove(client_socket)
        client_socket.close()
        print(f"[!] Client {addr} disconnected")

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[+] Server listening on {self.host}:{self.port}")
        
        while self.running:
            try:
                self.sock.settimeout(1)
                client, addr = self.sock.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(client, addr))
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[!] Error accepting connection: {e}")

class ToolRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): pass
        
    def do_GET(self):
        if self.path.startswith('/tools/'):
            tool_name = self.path.split('/')[-1].replace('.py', '')
            tool_code = ToolServer().get_tool(tool_name)
            if tool_code:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(tool_code.encode())
            else:
                self.send_response(404)
                self.end_headers()
        elif self.path.startswith('/libs/'):
            lib_name = self.path.split('/')[-1].replace('.py', '')
            lib_code = ToolServer().get_lib(lib_name)
            if lib_code:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(lib_code.encode())
            else:
                self.send_response(404)
                self.end_headers() 
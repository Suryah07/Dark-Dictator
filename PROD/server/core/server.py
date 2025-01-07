import socket
import json
import threading
import signal
import sys
import http.server
import socketserver
from .module_manager import ModuleManager

class CommandServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.module_manager = ModuleManager()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True
        self.clients = []
        signal.signal(signal.SIGINT, self.handle_shutdown)

    # ... rest of TestServer code but renamed to CommandServer ...

class ModuleRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, module_manager=None, **kwargs):
        self.module_manager = module_manager
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args): pass
        
    def do_GET(self):
        if self.path.startswith('/tools/'):
            tool_name = self.path.split('/')[-1].replace('.py', '')
            tool_code = self.module_manager.get_tool(tool_name)
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
            lib_code = self.module_manager.get_lib(lib_name)
            if lib_code:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(lib_code.encode())
            else:
                self.send_response(404)
                self.end_headers()

def start_servers(cmd_port=5555, http_port=8000):
    # Initialize module manager
    module_manager = ModuleManager()
    
    # Start HTTP server for modules
    handler = lambda *args, **kwargs: ModuleRequestHandler(*args, module_manager=module_manager, **kwargs)
    http_server = socketserver.TCPServer(('127.0.0.1', http_port), handler)
    http_thread = threading.Thread(target=http_server.serve_forever)
    http_thread.daemon = True
    http_thread.start()
    print(f"[+] Module server started on port {http_port}")

    # Start command server
    cmd_server = CommandServer('127.0.0.1', cmd_port)
    try:
        cmd_server.start()
    finally:
        http_server.shutdown()
        http_server.server_close() 
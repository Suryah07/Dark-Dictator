import socket
import socks
import requests
import stem.process
from stem.control import Controller
import tempfile
import os
import time
import sys
import base64
from .binary_handler import BinaryHandler

class TorHandler:
    def __init__(self):
        self.socks_port = self._get_free_port()
        self.control_port = self._get_free_port()
        self.tor_process = None
        self.data_directory = tempfile.mkdtemp()
        self.onion_port = None
        self.hidden_service_dir = None
        self.binary_handler = BinaryHandler()
        
    def _get_free_port(self):
        """Get a free port on the system"""
        s = socket.socket()
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def start_tor(self):
        """Start Tor process with SOCKS and control port"""
        try:
            # Extract Tor binary
            tor_path = self.binary_handler.extract_tor()
            if not tor_path:
                raise Exception("Failed to extract Tor binary")
                
            # Start Tor process
            self.tor_process = stem.process.launch_tor_with_config(
                config = {
                    'SocksPort': str(self.socks_port),
                    'ControlPort': str(self.control_port),
                    'DataDirectory': self.data_directory,
                },
                init_msg_handler = lambda line: print("[*] " + line if line else ""),
                tor_cmd = tor_path,
                take_ownership = True
            )
            return True
        except Exception as e:
            print(f"[!] Error starting Tor: {e}")
            return False

    def create_onion_service(self, target_port):
        """Create a hidden service"""
        try:
            with Controller.from_port(port=self.control_port) as controller:
                controller.authenticate()
                
                # Create hidden service
                hidden_service = controller.create_hidden_service(
                    path = os.path.join(self.data_directory, 'hidden_service'),
                    port = 80,
                    target_port = target_port
                )
                
                self.onion_port = hidden_service.service_id
                self.hidden_service_dir = hidden_service.path
                
                print(f"[+] Created onion service: {hidden_service.service_id}.onion")
                return hidden_service.service_id
                
        except Exception as e:
            print(f"[!] Error creating onion service: {e}")
            return None

    def setup_connection(self):
        """Configure SOCKS proxy for requests and socket"""
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", self.socks_port)
        socket.socket = socks.socksocket
        
        # Configure requests to use Tor
        session = requests.Session()
        session.proxies = {
            'http': f'socks5h://127.0.0.1:{self.socks_port}',
            'https': f'socks5h://127.0.0.1:{self.socks_port}'
        }
        return session

    def create_connection(self, onion, port):
        """Create a Tor connection to an onion service"""
        sock = socks.socksocket()
        sock.set_proxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", self.socks_port)
        sock.connect((f"{onion}.onion", port))
        return sock

    def get_new_identity(self):
        """Request new Tor circuit"""
        try:
            with Controller.from_port(port=self.control_port) as controller:
                controller.authenticate()
                controller.signal("NEWNYM")
                time.sleep(5)  # Wait for new circuit
                return True
        except Exception as e:
            print(f"[!] Error getting new identity: {e}")
            return False

    def cleanup(self):
        """Clean up Tor process and temporary files"""
        if self.tor_process:
            self.tor_process.kill()
        try:
            if self.hidden_service_dir:
                shutil.rmtree(self.hidden_service_dir)
            os.rmdir(self.data_directory)
            self.binary_handler.cleanup()
        except:
            pass 
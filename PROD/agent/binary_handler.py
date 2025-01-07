import os
import sys
import tempfile
import base64
import subprocess
import shutil
from pathlib import Path

class BinaryHandler:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tor_binary = None
        self.tor_data = None
        
    def _get_embedded_tor(self):
        """Get embedded Tor binary data"""
        # This will be replaced with actual binary data during build
        return """
        <<TOR_BINARY_BASE64>>
        """
        
    def extract_tor(self):
        """Extract Tor binary to temp directory"""
        try:
            # Get binary data and decode
            tor_data = self._get_embedded_tor().strip()
            binary_data = base64.b64decode(tor_data)
            
            # Determine binary name based on platform
            if sys.platform == 'win32':
                binary_name = 'tor.exe'
            else:
                binary_name = 'tor'
                
            # Save binary to temp directory
            self.tor_binary = os.path.join(self.temp_dir, binary_name)
            with open(self.tor_binary, 'wb') as f:
                f.write(binary_data)
                
            # Make binary executable on Unix
            if sys.platform != 'win32':
                os.chmod(self.tor_binary, 0o755)
                
            return self.tor_binary
            
        except Exception as e:
            print(f"[!] Error extracting Tor binary: {e}")
            return None
            
    def cleanup(self):
        """Clean up extracted files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except:
            pass 
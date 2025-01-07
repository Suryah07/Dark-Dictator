import os
import base64
import shutil
from pathlib import Path

def embed_tor_binary():
    """Embed Tor binary into the agent code"""
    # Path to your Tor binary
    if os.name == 'nt':
        tor_path = "binaries/tor.exe"
    else:
        tor_path = "binaries/tor"
        
    # Read binary data
    with open(tor_path, 'rb') as f:
        binary_data = f.read()
        
    # Encode as base64
    encoded_data = base64.b64encode(binary_data).decode()
    
    # Read binary handler template
    with open('agent/binary_handler.py', 'r') as f:
        code = f.read()
        
    # Replace placeholder with actual binary data
    code = code.replace('<<TOR_BINARY_BASE64>>', encoded_data)
    
    # Write updated code
    with open('agent/binary_handler.py', 'w') as f:
        f.write(code)

def main():
    # Create binaries directory structure
    os.makedirs('PROD/binaries', exist_ok=True)
    
    # Copy Tor binaries to build directory
    if os.name == 'nt':
        shutil.copy('path/to/tor.exe', 'PROD/binaries/tor.exe')
    else:
        shutil.copy('path/to/tor', 'PROD/binaries/tor')
        
    # Embed binary in code
    embed_tor_binary()
    
    # Build agent
    os.system('pyinstaller --onefile --noconsole PROD/agent/agent.py')

if __name__ == '__main__':
    main() 
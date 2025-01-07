import os
import shutil
import subprocess
import sys
import logging

def setup_build_environment(language):
    """Setup the build environment based on selected language"""
    try:
        # Get current working directory (should be GUI_server)
        current_dir = os.getcwd()
        
        # Create necessary directories
        os.makedirs(os.path.join(current_dir, 'dist'), exist_ok=True)
        os.makedirs(os.path.join(current_dir, 'tools'), exist_ok=True)
        os.makedirs(os.path.join(current_dir, 'torbundle'), exist_ok=True)
        
        # Get the base directory path (project root)
        base_dir = os.path.dirname(current_dir)
        agent_client_dir = os.path.join(base_dir, 'agent_client')
        
        logging.info(f"Setting up build environment in {current_dir}")
        logging.info(f"Agent client directory: {agent_client_dir}")
        
        # Source paths with absolute paths
        agent_src = os.path.join(agent_client_dir, f'agent.{"py" if language == "python" else "cpp"}')
        tor_network_src = os.path.join(agent_client_dir, 'tor_network.py')
        tools_src = os.path.join(agent_client_dir, 'tools')
        torbundle_src = os.path.join(agent_client_dir, 'torbundle', 'tor.zip')
        
        # Copy files
        if os.path.exists(agent_src):
            shutil.copy2(agent_src, os.path.join(current_dir, f'agent.{"py" if language == "python" else "cpp"}'))
            logging.info(f"Copied agent source from {agent_src}")
        else:
            raise Exception(f"Agent source file not found: {agent_src}")
            
        if language == 'python':
            # Copy Python-specific files
            if os.path.exists(tor_network_src):
                shutil.copy2(tor_network_src, os.path.join(current_dir, 'tor_network.py'))
                logging.info("Copied tor_network.py")
            else:
                raise Exception(f"Tor network file not found: {tor_network_src}")
            
            # Copy tools directory
            tools_dest = os.path.join(current_dir, 'tools')
            if os.path.exists(tools_dest):
                shutil.rmtree(tools_dest)
            if os.path.exists(tools_src):
                shutil.copytree(tools_src, tools_dest)
                logging.info("Copied tools directory")
            else:
                raise Exception(f"Tools directory not found: {tools_src}")
        
        # Copy tor bundle
        torbundle_dest = os.path.join(current_dir, 'torbundle', 'tor.zip')
        if os.path.exists(torbundle_dest):
            os.remove(torbundle_dest)
        if os.path.exists(torbundle_src):
            shutil.copy2(torbundle_src, torbundle_dest)
            logging.info("Copied tor bundle")
        else:
            raise Exception(f"Tor bundle not found: {torbundle_src}")
        
        # Setup language-specific requirements
        if language == 'python':
            # Install Python requirements
            requirements_file = os.path.join(agent_client_dir, 'requirements.txt')
            if os.path.exists(requirements_file):
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', requirements_file], check=True)
                logging.info("Installed Python requirements")
        else:
            # Check for C++ compiler
            try:
                subprocess.run(['g++', '--version'], check=True, capture_output=True)
                logging.info("Found C++ compiler")
            except subprocess.CalledProcessError:
                raise Exception("C++ compiler (g++) not found")
            
            # Check for required C++ libraries
            cpp_libs = ['boost', 'openssl', 'curl']
            for lib in cpp_libs:
                if not check_cpp_library(lib):
                    raise Exception(f"Required C++ library not found: {lib}")
        
        logging.info(f"Build environment setup complete for {language}")
        return True
        
    except Exception as e:
        logging.error(f"Error setting up build environment: {e}")
        return False

def check_cpp_library(library):
    """Check if a C++ library is installed"""
    try:
        if sys.platform == 'linux':
            subprocess.run(['pkg-config', '--exists', library], check=True)
        elif sys.platform == 'win32':
            # On Windows, we might check specific paths or registry
            return True  # Implement proper check for Windows
        return True
    except subprocess.CalledProcessError:
        return False

def append_address(filename, onion, port):
    """Append onion address and port to the executable"""
    try:
        with open(filename, 'ab') as f:
            f.write(onion.encode())
            port_str = str(port).zfill(5)
            f.write(port_str.encode())
        logging.info(f"Successfully appended address to {filename}")
        return True
    except Exception as e:
        logging.error(f"Error appending address: {e}")
        return False 
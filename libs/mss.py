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
            self.monitors = [{'left': 0, 'top': 0, 'width': 1920, 'height': 1080}]

    def grab(self, monitor):
        if sys.platform == 'win32':
            return self._grab_win32(monitor)
        else:
            return self._grab_test(monitor)

    def _grab_win32(self, monitor):
        width, height = monitor['width'], monitor['height']
        
        hwnd = windll.user32.GetDesktopWindow()
        wDC = windll.user32.GetWindowDC(hwnd)
        dcObj = windll.gdi32.CreateCompatibleDC(wDC)
        
        bmp = windll.gdi32.CreateCompatibleBitmap(wDC, width, height)
        windll.gdi32.SelectObject(dcObj, bmp)
        
        windll.gdi32.BitBlt(
            dcObj, 0, 0, width, height,
            wDC, monitor['left'], monitor['top'],
            0x00CC0020  # SRCCOPY
        )
        
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height
        bmi.biPlanes = 1
        bmi.biBitCount = 24
        bmi.biCompression = 0
        
        size = height * width * 3
        data = create_string_buffer(size)
        windll.gdi32.GetDIBits(
            dcObj, bmp, 0, height,
            data, byref(bmi), 0
        )
        
        windll.gdi32.DeleteObject(bmp)
        windll.gdi32.DeleteDC(dcObj)
        windll.user32.ReleaseDC(hwnd, wDC)
        
        return SimpleNamespace(rgb=data.raw, size=(width, height))

    def _grab_test(self, monitor):
        width, height = monitor['width'], monitor['height']
        size = width * height * 3
        data = (ctypes.c_ubyte * size)()
        return SimpleNamespace(rgb=bytes(data), size=(width, height))

    def to_png(self, data, size):
        width, height = size
        line = width * 3
        
        png_data = bytearray()
        for y in range(height):
            png_data.append(0)
            png_data.extend(data[y*line:(y+1)*line])
        
        header = struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0)
        ihdr = self._create_chunk(b'IHDR', header)
        idat = self._create_chunk(b'IDAT', zlib.compress(png_data, self.compression_level))
        iend = self._create_chunk(b'IEND', b'')
        
        return b'\x89PNG\r\n\x1a\n' + ihdr + idat + iend

    def _create_chunk(self, type_code, data):
        chunk = type_code + data
        return struct.pack('!I', len(data)) + chunk + struct.pack('!I', zlib.crc32(chunk))

    def __enter__(self): return self
    def __exit__(self, *args): pass

def mss(): return MSS() 
import os
from mss import mss
from datetime import datetime
import tempfile
from PIL import Image
import io

class Screenshot:
    def __init__(self):
        self.sct = mss()

    def capture(self):
        """Take a screenshot and return the image data
        Returns:
            tuple: (success, message, image_data)
        """
        try:
            # Capture the entire screen (first monitor)
            monitor = self.sct.monitors[1]  # 1 is the main monitor
            screenshot = self.sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            
            # Save to bytes buffer in PNG format
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            png_bytes = img_buffer.getvalue()
            
            if png_bytes:
                return True, "Screenshot captured successfully", png_bytes
            else:
                return False, "Failed to capture screenshot", None
                
        except Exception as e:
            return False, f"Screenshot error: {str(e)}", None
        finally:
            try:
                img_buffer.close()
            except:
                pass
        
    def cleanup(self):
        """Clean up resources"""
        try:
            self.sct.close()
        except:
            pass 
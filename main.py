import socket
import threading
import sys
import os
import stem.process
import stat
from shell_ui.style import (
    Style,
    ProgressSpinner
)


class Tor:
    """
    A class to handle the tor process,
    and the tor hidden service.
    """
    BASE_DIR = 'hidden_service'
    TORRC_PATH = os.path.join('hidden_service', 'torrc')
    
    TOR_SOCKS_PORT = 9200

    def __init__(self, name, listener_port, forward_port):
        self.name = name
        # listen and forward port configured in /etc/tor/torrc
        self.listener_port = listener_port
        self.forward_port = forward_port

        # create hidden service directory
        if not os.path.isdir(self.BASE_DIR):
            print("Creating hdden")
            os.mkdir(self.BASE_DIR)
            # the owner has full permissions over dir (equivalent to chmod 700)
            os.chmod(self.BASE_DIR, stat.S_IRWXU)
        print(self.BASE_DIR,Tor.TORRC_PATH)

        ps = ProgressSpinner('Starting Tor Process')
        ps.start()
        self.tor_process = self.launch()
        ps.stop()
        print()
        Style.pos_sys_msg('Onion: {}'.format(self.get_onion_address()))

    def launch(self):
        tor_process = stem.process.launch_tor_with_config(
            config={
                'SocksListenAddress': '127.0.0.1:{}'.format(self.TOR_SOCKS_PORT),
                'SocksPort': '{}'.format(self.TOR_SOCKS_PORT),
                'HiddenServiceDir': '{}'.format(self.BASE_DIR),
                'HiddenServiceVersion': '3',
                'HiddenServicePort': '{} 127.0.0.1:{}'.format(self.listener_port, self.forward_port),
                'torrc_path': '{}'.format(Tor.TORRC_PATH)
            })
        return tor_process

    def get_onion_address(self):
        with open(os.path.join(self.BASE_DIR, 'hostname'), 'r') as f:
            # remove \n from hostname file
            return f.read().rstrip()

sam = Tor("tot",8333,9090)

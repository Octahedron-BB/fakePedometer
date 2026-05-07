import os
import subprocess
import platform
import time
import sys

def set_proxy(enable=True):
    """自动判断操作系统并开关代理服务器"""
    system = platform.system()
    
    if system == "Darwin":  # macOS (MacBook)
        if enable:
            print("[*] 正在为 Mac (Wi-Fi) 开启代理服务器...")
            os.system("networksetup -setwebproxy Wi-Fi 127.0.0.1 8080")
            os.system("networksetup -setsecurewebproxy Wi-Fi 127.0.0.1 8080")
        else:
            print("[*] 正在还原 Mac 代理设定...")
            os.system("networksetup -setwebproxystate Wi-Fi off")
            os.system("networksetup -setsecurewebproxystate Wi-Fi off")
            
    elif system == "Windows":  # Windows 系統
        if enable:
            print("[*] 正在为 Windows 开启代理服务器...")
            os.system('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable /t REG_DWORD /d 1 /f >nul 2>&1')
            os.system('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyServer /t REG_SZ /d "127.0.0.1:8080" /f >nul 2>&1')
        else:
            print("[*] 正在还原 Windows 代理设定...")
            os.system('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul 2>&1')

def main():
    try:
        print("========================================")
        print("      万步网数据拦截器 - 安全启动模式     ")
        print("========================================")
        
        # 1. 安全开启代理
        set_proxy(enable=True)
        print("[+] 系统代理已切换至 127.0.0.1:8080")
        print("\n👉 【操作指示】")
        print("   1. 请现在开启万步网软件。")
        print("   2. 插上计步器，点击“同步”。")
        print("   3. 看到“成功提取 session.json”后，按下 Ctrl+C 关闭此窗口。\n")
        
        # 2. 启动 mitmdump (拦截脚本)
        # 这里会卡住并持续监听，直到用户按下 Ctrl+C
        subprocess.run(["mitmdump", "-s", "sniffer.py", "-p", "8080"])
        
    except FileNotFoundError:
        print("\n[!] 错误：找不到 mitmdump！")
        print("请确保你已经在终端机执行过： pip install mitmproxy")
    except KeyboardInterrupt:
        # 当用户按下 Ctrl+C 时，会触发这个中断
        print("\n\n[!] 收到关闭指令 (Ctrl+C)，准备安全退出...")
    finally:
        # 3. 确保无论发生什么事，一定会把代理关掉
        set_proxy(enable=False)
        print("[+] 系统网络已恢复正常，安全退出。")
        print("========================================")
        time.sleep(1) # 让用户看一眼提示

if __name__ == "__main__":
    main()
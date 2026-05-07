import json
import urllib.parse
from mitmproxy import http
import os

class WanbuInterceptor:
    def request(self, flow: http.HTTPFlow):
        # 1. 锁定目标：只拦截发往万步网同步 API 的请求
        if "sync.wanbu.com.cn" in flow.request.pretty_host and "PCPedUploadFlowsService" in flow.request.path:
            
            # 获取请求的内容 (URL Encoded 格式)
            body = flow.request.get_text()
            
            # 2. 精准狙击：找到真正要上传数据的 pcUploadData 请求
            if "pcUploadData" in body or "newUploadData" in body:
                print("\n[!] 🚨 侦测到万步网同步请求！开始进行拦截...")
                
                try:
                    # 将 URL 编码解开，提取 ReqMessageBody 的 JSON 字符串
                    parsed_body = urllib.parse.parse_qs(body)
                    req_msg_body_str = parsed_body.get("ReqMessageBody", [""])[0]
                    
                    if not req_msg_body_str:
                        return
                        
                    data = json.loads(req_msg_body_str)
                    
                    # 3. 提取我们需要的关键参数
                    session_data = {
                        "accessToken": data.get("accessToken"),
                        "deviceSerial": data.get("deviceserial"),
                        # 截取目前的序号，generator.py 读取时会自动 +1
                        "lastDayId": int(data.get("dayPackage", 4)),
                        "lastHourId": int(data.get("hourPackage", 38))
                    }
                    
                    # 从 listday 里面提取用户的生理与设备参数
                    listday = data.get("listday", [])
                    if listday:
                        session_data["stepWidth"] = listday[0].get("stepWidth", 70)
                        session_data["weight"] = listday[0].get("weight", 60.0)
                    
                    # 4. 存储为 session.json 供第二天脚本使用
                    with open("session.json", "w", encoding="utf-8") as f:
                        json.dump(session_data, f, indent=4)
                        
                    print("[+] 📦 成功提取并存储 session.json，参数如下：")
                    print(json.dumps(session_data, indent=2))
                    
                    # 5. 终极防御：杀掉这个请求！
                    # 这样你的 0 步数据就绝对不会污染服务器的数据库
                    flow.kill()
                    print("[+] 🛡️ 已成功阻断原始 0 步数据上传！云端历史记录安全无虞。")
                    print("[*] 👉 现在你可以按 Ctrl+C 关闭此程序，并运行 generator.py 了。")
                    
                except Exception as e:
                    print(f"[-] ❌ 解析数据包时发生错误: {e}")

# 注册拦截器
addons = [
    WanbuInterceptor()
]
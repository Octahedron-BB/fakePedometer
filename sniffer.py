import json
import urllib.parse
from mitmproxy import http
import os
from datetime import datetime

import accounts

class WanbuInterceptor:
    def request(self, flow: http.HTTPFlow):
        # 1. 锁定目标：只拦截发往万步网同步 API 的请求
        if "sync.wanbu.com.cn" in flow.request.pretty_host and "PCPedUploadFlowsService" in flow.request.path:
            
            # 获取请求的内容 (URL Encoded 格式)
            body = flow.request.get_text()
            
            # 2. 精准狙击：找到真正要上传数据的 pcUploadData 请求
            if "pcUploadData" in body or "newUploadData" in body:
                print("\n" + "="*40)
                print("[!] 🚨 侦测到万步网同步请求！开始处理...")
                
                try:
                    # 将 URL 编码解开，提取 ReqMessageBody 的 JSON 字符串
                    parsed_body = urllib.parse.parse_qs(body)
                    req_msg_body_str = parsed_body.get("ReqMessageBody", [""])[0]
                    
                    if not req_msg_body_str:
                        return
                        
                    data = json.loads(req_msg_body_str)

                    # 3. 提取 session.json 所需参数
                    session_data = {
                        "accessToken": data.get("accessToken"),
                        "deviceSerial": data.get("deviceserial"),
                        # 自动获取当前序号，Generator 会在此基础上累加
                        "lastDayId": int(data.get("dayPackage", 4)),
                        "lastHourId": int(data.get("hourPackage", 38)),
                        "clientvison": data.get("clientvison", "6.5.3"),  # 顺手存下版本号
                        # 记录抓包时间，用于判断 token（约 3 天）是否过期
                        "capturedAt": datetime.now().isoformat(timespec="seconds")
                    }
                    serial = session_data["deviceSerial"]
                    if not serial:
                        print("[!] 抓包中未找到 deviceserial，跳过该请求。")
                        return

                    # 提取生理参数
                    listday = data.get("listday", [])
                    if listday:
                        # 找最新的那一天提取参数
                        session_data["stepWidth"] = listday[-1].get("stepWidth", 70)
                        session_data["weight"] = listday[-1].get("weight", 60.0)

                    # 若该设备已有账户，保留备注名与最近同步日期
                    old = accounts.load_session(serial)
                    is_new = old is None
                    if old:
                        for k in ("name", "lastSyncDate"):
                            if old.get(k):
                                session_data[k] = old[k]

                    # 4. 存储到对应账户目录
                    accounts.save_session(serial, session_data)
                    accounts.save_capture(serial, data)
                    print("[+] 📂 完整步数历史已存至: " + accounts.capture_path(serial))
                    print(f"[+] 📦 模拟器凭证已更新到账户: {serial} ({'新账户' if is_new else '已有账户'})")
                    
                    # 5. 终极防御：杀掉原始请求
                    flow.kill()
                    print("[+] 🛡️ 已拦截原始数据，防止 0 步覆盖云端。")
                    print("="*40 + "\n")
                    
                except Exception as e:
                    print(f"[-] ❌ 拦截处理失败: {e}")

# 注册拦截器
addons = [
    WanbuInterceptor()
]
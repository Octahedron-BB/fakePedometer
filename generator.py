import json
import random
import time
import requests
from datetime import datetime, timedelta
import os

DB_FILE = "my_steps_db.json"

class HumanGenerator:
    def __init__(self, session):
        self.session = session
        self.step_width = int(session.get("stepWidth", 70))
        self.weight = float(session.get("weight", 60.0))
        self.token = session.get("accessToken")
        self.device_serial = session.get("deviceSerial")
        self.db = self.load_db()

    def load_db(self):
        """读取本地数据库"""
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_db(self):
        """保存到本地数据库"""
        with open(DB_FILE, "w") as f:
            json.dump(self.db, f, indent=4)

    def get_or_create_day(self, date_str):
        """获取或初始化当天数据结构"""
        if date_str not in self.db:
            self.db[date_str] = {
                "listhour": {f"hour{i}": "0,0,0,0,0,0" for i in range(26)},
                "is_morning_done": False,
                "is_afternoon_done": False
            }
        return self.db[date_str]

    def calculate_physics(self, steps, is_task):
        if steps == 0: return 0, 0.0, 0, 0
        
        if is_task:
            cadence = random.randint(115, 138)
            eff_rate, fast_rate = random.uniform(0.96, 0.99), random.uniform(0.92, 0.98)
            ex_factor = 1.6
        else:
            cadence = random.randint(60, 95)
            eff_rate, fast_rate = random.uniform(0.30, 0.65), random.uniform(0.0, 0.10)
            ex_factor = 0.7

        w_time = max(1, steps // cadence)
        return w_time, round((steps * self.step_width) / 100000 * ex_factor, 2), int(steps * eff_rate), int(steps * fast_rate)

    def generate_incremental(self):
        """增量生成当天步数（只填补还没生成的过去小时）"""
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        day_data = self.get_or_create_day(date_str)
        current_hour = now.hour
        
        hours_db = day_data["listhour"]
        
        # 找出哪些过去的小时还是空的 (尚未生成)
        empty_past_hours = [h for h in range(7, current_hour) if hours_db[f"hour{h}"] == "0,0,0,0,0,0"]
        
        if not empty_past_hours:
            print("[*] 当前时间之前的数据已生成完毕，无需新增。")
            return date_str

        # 1. 补齐朝朝任务 (07:00-08:59)
        if current_hour >= 8 and not day_data["is_morning_done"]:
            available = [h for h in empty_past_hours if h in [7, 8]]
            if available:
                slot = random.choice(available)
                steps = random.randint(3200, 3600)
                wt, ex, eff, fst = self.calculate_physics(steps, True)
                d = steps * self.step_width
                hours_db[f"hour{slot}"] = f"{steps},{d},{fst},{fst*self.step_width},{eff},{eff*self.step_width}"
                empty_past_hours.remove(slot)
                day_data["is_morning_done"] = True

        # 2. 补齐下午任务 (15min + 15min)
        if current_hour >= 10 and not day_data["is_afternoon_done"] and empty_past_hours:
            slot = random.choice(empty_past_hours)
            steps = random.randint(3800, 4500)
            wt, ex, eff, fst = self.calculate_physics(steps, True)
            d = steps * self.step_width
            hours_db[f"hour{slot}"] = f"{steps},{d},{fst},{fst*self.step_width},{eff},{eff*self.step_width}"
            empty_past_hours.remove(slot)
            day_data["is_afternoon_done"] = True

        # 3. 填补日常零碎步数
        if empty_past_hours:
            # 决定今天要再走几步 (确保总步数合理)
            fill_count = random.randint(1, len(empty_past_hours))
            fill_slots = random.sample(empty_past_hours, fill_count)
            for slot in fill_slots:
                steps = random.randint(200, 1500)
                wt, ex, eff, fst = self.calculate_physics(steps, False)
                d = steps * self.step_width
                hours_db[f"hour{slot}"] = f"{steps},{d},{fst},{fst*self.step_width},{eff},{eff*self.step_width}"

        self.save_db()
        return date_str

    def calculate_daily_summary(self, date_str):
        """根据 listhour 计算出当天的 listday 总和"""
        hours_db = self.db[date_str]["listhour"]
        total_s, total_eff, total_fast, total_time, total_ex = 0, 0, 0, 0, 0.0
        morning_sum = 0
        
        for i in range(26):
            data_str = hours_db[f"hour{i}"]
            parts = [int(x) for x in data_str.split(",")]
            if parts[0] > 0:
                steps, _, fast_s, _, eff_s, _ = parts
                wt, ex, _, _ = self.calculate_physics(steps, is_task=(steps>3000)) # 逆向推算时间与运动量
                
                total_s += steps
                total_eff += eff_s
                total_fast += fast_s
                total_time += wt
                total_ex += ex
                
                if i in [5, 6, 7, 8]: morning_sum += steps

        return {
            "stepNumber": total_s,
            "walkDistance": total_s * self.step_width,
            "remaineffectiveSteps": total_eff,
            "faststepnum": total_fast,
            "walkdate": date_str,
            "stepWidth": self.step_width,
            "weight": self.weight,
            "walkTime": total_time,
            "exerciseAmount": round(total_ex, 2),
            "calorieConsumed": round(total_s * 0.04, 2),
            "fatConsumed": round(total_s * 0.005, 2),
            "zmrule": "5,6,7,8#3000;17,18,19,20,21,22#4000",
            "zmstatus": "1,0" if morning_sum >= 3000 else "0,0"
        }

    def build_payload(self):
        # 1. 先进行当天的增量生成并存档
        today_str = self.generate_incremental()
        
        # 2. 获取最近 3 天的数据打包 (如果有的话)
        dates_to_upload = sorted(self.db.keys())[-3:] 
        
        list_day, list_hour, list_recipe = [], [], []
        
        for d_str in dates_to_upload:
            day_summary = self.calculate_daily_summary(d_str)
            list_day.append(day_summary)
            
            # 组装 listhour
            h_data = self.db[d_str]["listhour"].copy()
            h_data["walkdate"] = d_str
            list_hour.append(h_data)
            
            # 组装 recipe
            list_recipe.append({
                "recipenumber": 9999,
                "task1state": 1, "task2state": 1, "task3state": 1, "task4state": 1,
                "task5state": 2, "task6state": 2, "task7state": 2, "task8state": 2,
                "walkdate": d_str
            })

        payload = {
            "accessToken": self.token,
            "commond": "newUploadData",
            "dayPackage": str(self.session["lastDayId"]),
            "hourPackage": str(int(self.session.get("lastHourId", 39)) + 1),
            "deviceType": "TW726",
            "deviceserial": self.device_serial,
            "reqservicetype": "0",
            "sequenceID": str(int(time.time())),
            "clientvison": "6.5.3",
            "listRecipeData": list_recipe,
            "listday": list_day,
            "listhour": list_hour
        }
        return payload, list_day[-1] # 返回 payload 和今天的总结供显示

    def run(self):
        payload_body, today_summary = self.build_payload()
        post_data = {
            "commond": "pcUploadData",
            "ReqMessageBody": json.dumps(payload_body, separators=(',', ':'))
        }
        
        print(f"[*] 数据整合完毕！本日已累计总步数: {today_summary['stepNumber']}")
        print(f"[*] 有效步数: {today_summary['remaineffectiveSteps']} | 总用时: {today_summary['walkTime']} 分钟")
        
        try:
            res = requests.post("http://sync.wanbu.com.cn/WanbuDataServer_NEW/PCPedUploadFlowsService", 
                                data=post_data, headers={"User-Agent": "PEB_CTRL", "Content-Type": "application/x-www-form-urlencoded"})
            if '"resultCode":"0000"' in res.text:
                print("[+] 同步成功！记忆已保存至 my_steps_db.json")
                
                # --- 关键修正：成功后更新 session.json 的序号 ---
                self.session["lastHourId"] = int(payload_body["hourPackage"])
                # 如果跨天了，也可以推进 DayId (简单判断：如果目前的日期大于上次抓包的日期)
                # self.session["lastDayId"] = int(payload_body["dayPackage"]) # 视服务器严格程度而定，通常 hour 推进最重要
                
                with open("session.json", "w") as f:
                    json.dump(self.session, f, indent=4)
                print(f"[*] 通行证序号已自动推进至: {self.session['lastHourId']}")
                
            else:
                print(f"[!] 服务器报错: {res.text}")
        except Exception as e:
            print(f"[!] 网络异常: {e}")

if __name__ == "__main__":
    if os.path.exists("session.json"):
        with open("session.json", "r") as f:
            HumanGenerator(json.load(f)).run()
    else:
        print("[!] 找不到 session.json。")
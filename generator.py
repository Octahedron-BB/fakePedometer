import json
import random
import time
import requests
from datetime import datetime, timedelta
import os

DB_FILE = "my_steps_db.json"
HISTORY_FILE = "captured_history.json" 

class HumanGenerator:
    def __init__(self, session):
        self.session = session
        self.step_width = int(session.get("stepWidth", 70))
        self.weight = float(session.get("weight", 60.0))
        self.token = session.get("accessToken")
        self.device_serial = session.get("deviceSerial")
        
        # 初始序号
        self.last_day_id = int(session.get("lastDayId", 5))
        self.last_hour_id = int(session.get("lastHourId", 60))
        self.last_sync_date = session.get("lastSyncDate", datetime.now().strftime("%Y%m%d"))
        
        self.db = self.load_db()
        # 1. 先同步硬件数据
        self.sync_from_capture()

    def load_db(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_db(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.db, f, indent=4)

    def get_or_create_day(self, date_str):
        if date_str not in self.db:
            self.db[date_str] = {
                "listhour": {f"hour{i}": "0,0,0,0,0,0" for i in range(26)},
                "is_morning_done": False,
                "is_afternoon_done": False
            }
        return self.db[date_str]

    def sync_from_capture(self):
        """同步硬件抓包数据并执行安全校验"""
        if not os.path.exists(HISTORY_FILE): return
        
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            capture = json.load(f)
            
        print(f"[*] 正在从 {HISTORY_FILE} 合并硬件数据...")
        
        # 1. 序号防倒退机制：只取最大值
        cap_day = int(capture.get("dayPackage", 0))
        cap_hour = int(capture.get("hourPackage", 0))
        
        self.last_day_id = max(self.last_day_id, cap_day)
        self.last_hour_id = max(self.last_hour_id, cap_hour)

        # 2. 合并步数数据 (保护机制：只覆盖本地为 0 的空数据)
        for h_item in capture.get("listhour", []):
            d_str = h_item["walkdate"]
            day_data = self.get_or_create_day(d_str)
            for i in range(26):
                h_key = f"hour{i}"
                # 如果硬件有数据，并且本地对应小时还是 0，才进行合并
                if h_item.get(h_key) and h_item[h_key] != "0,0,0,0,0,0":
                    if day_data["listhour"][h_key] == "0,0,0,0,0,0":
                        day_data["listhour"][h_key] = h_item[h_key]

        # 3. 合并处方状态
        for r_item in capture.get("listRecipeData", []):
            d_str = r_item["walkdate"]
            day_data = self.get_or_create_day(d_str)
            if r_item.get("task1state") == 1: day_data["is_morning_done"] = True
            if r_item.get("task5state") == 1: day_data["is_afternoon_done"] = True
            
        self.save_db()
        
        # 4. 【关键】阅后即焚/归档，防止下次无限循环读取旧文件
        try:
            bak_filename = f"captured_history_{int(time.time())}.bak"
            os.rename(HISTORY_FILE, bak_filename)
            print(f"[+] 抓包文件已处理完毕并归档为: {bak_filename} (防止重复读取)")
        except Exception as e:
            print(f"[!] 归档失败，请下次运行前手动删除 {HISTORY_FILE}。错误: {e}")

    def calculate_physics(self, steps, is_task):
        if steps <= 0: return 0, 0.0, 0, 0
        cadence = random.randint(115, 138) if is_task else random.randint(60, 95)
        eff_rate = random.uniform(0.96, 0.99) if is_task else random.uniform(0.30, 0.65)
        fast_rate = random.uniform(0.92, 0.98) if is_task else random.uniform(0.0, 0.10)
        ex_factor = 1.6 if is_task else 0.7
        w_time = max(1, int(steps // cadence))
        return w_time, round((steps * self.step_width) / 100000 * ex_factor, 2), int(steps * eff_rate), int(steps * fast_rate)

    def complete_historical_day(self, date_str):
        """对【往日】执行全量补全"""
        print(f"[*] 正在全量补全历史日期: {date_str}")
        day_data = self.get_or_create_day(date_str)
        hours_db = day_data["listhour"]
        if not day_data["is_morning_done"]:
            steps = random.randint(3200, 3600); _, _, eff, fst = self.calculate_physics(steps, True)
            hours_db["hour7"] = f"{steps},{steps*self.step_width},{fst},{fst*self.step_width},{eff},{eff*self.step_width}"
            day_data["is_morning_done"] = True
        if not day_data["is_afternoon_done"]:
            steps = random.randint(4100, 4800); _, _, eff, fst = self.calculate_physics(steps, True)
            hours_db["hour18"] = f"{steps},{steps*self.step_width},{fst},{fst*self.step_width},{eff},{eff*self.step_width}"
            day_data["is_afternoon_done"] = True
        
        total_s = sum([int(v.split(',')[0]) for k, v in hours_db.items() if k.startswith('hour')])
        if total_s < 10500:
            target_steps = random.randint(10500, 12000)
            gap = target_steps - total_s
            target_h = random.choice([10, 14, 16, 20])
            orig_s = int(hours_db[f"hour{target_h}"].split(',')[0]); new_s = orig_s + gap
            _, _, eff, fst = self.calculate_physics(new_s, is_task=(new_s > 3000))
            hours_db[f"hour{target_h}"] = f"{new_s},{new_s*self.step_width},{fst},{fst*self.step_width},{eff},{eff*self.step_width}"

    def generate_today_incremental(self):
        """对【当日】执行增量填充 (只填充过去的小时)"""
        now = datetime.now(); date_str = now.strftime("%Y%m%d")
        print(f"[*] 正在对今日执行增量模拟: {date_str}")
        day_data = self.get_or_create_day(date_str); current_hour = now.hour
        hours_db = day_data["listhour"]
        empty_past_hours = [h for h in range(7, current_hour) if hours_db[f"hour{h}"] == "0,0,0,0,0,0"]
        
        if current_hour >= 8 and not day_data["is_morning_done"]:
            available = [h for h in empty_past_hours if h in [7, 8]]
            if available:
                slot = random.choice(available); steps = random.randint(3200, 3600)
                _, _, eff, fst = self.calculate_physics(steps, True)
                hours_db[f"hour{slot}"] = f"{steps},{steps*self.step_width},{fst},{fst*self.step_width},{eff},{eff*self.step_width}"
                day_data["is_morning_done"] = True
                if slot in empty_past_hours: empty_past_hours.remove(slot)

        for slot in empty_past_hours:
            if random.random() > 0.4:
                steps = random.randint(200, 1200); _, _, eff, fst = self.calculate_physics(steps, False)
                hours_db[f"hour{slot}"] = f"{steps},{steps*self.step_width},{fst},{fst*self.step_width},{eff},{eff*self.step_width}"

    def calculate_daily_summary(self, date_str):
        hours_db = self.db[date_str]["listhour"]
        total_s, total_eff, total_fast, total_time, total_ex = 0, 0, 0, 0, 0.0
        
        m_steps = 0
        a_steps = 0

        for i in range(26):
            parts = [int(x) for x in hours_db[f"hour{i}"].split(",")]
            if parts[0] > 0:
                s, _, f_s, _, e_s, _ = parts
                wt, ex, _, _ = self.calculate_physics(s, is_task=(s > 3000))
                total_s += s; total_eff += e_s; total_fast += f_s; total_time += wt; total_ex += ex
                
                if 5 <= i <= 9:
                    m_steps += s
                if 17 <= i <= 22:
                    a_steps += s
       
        zm_m = 1 if m_steps >= 3000 else 0
        zm_a = 1 if a_steps >= 4000 else 0

        return {
            "calorieConsumed": float(round(total_s * 0.04, 2)),
            "exerciseAmount": float(round(total_ex, 2)),
            "faststepnum": int(total_fast),
            "fatConsumed": float(round(total_s * 0.005, 2)),
            "goalStepNum": 10000, 
            "remaineffectiveSteps": int(total_eff),
            "stepNumber": int(total_s),
            "stepWidth": self.step_width,
            "walkDistance": int(total_s * self.step_width),
            "walkTime": int(total_time),
            "walkdate": date_str,
            "weight": self.weight,
            "zmrule": "5,6,7,8#3000;17,18,19,20,21,22#4000",
            "zmstatus": f"{zm_m},{zm_a}"
        }

    def build_payload(self):
        today_str = datetime.now().strftime("%Y%m%d")
        
        # --- 新增：跨天自动推进 dayPackage ---
        if today_str > self.last_sync_date:
            d1 = datetime.strptime(self.last_sync_date, "%Y%m%d")
            d2 = datetime.strptime(today_str, "%Y%m%d")
            delta_days = (d2 - d1).days
            if delta_days > 0:
                self.last_day_id += delta_days
                print(f"[*] 检测到距离上次同步跨越了 {delta_days} 天，dayPackage 自动推进至: {self.last_day_id}")

        all_dates = sorted(self.db.keys())
        for d_str in all_dates:
            if d_str < today_str:
                self.complete_historical_day(d_str)
            elif d_str == today_str:
                self.generate_today_incremental()
        self.save_db()

        list_day, list_hour, list_recipe = [], [], []
        for d_str in all_dates[-7:]:
            summary = self.calculate_daily_summary(d_str)
            list_day.append(summary)
            h_data = self.db[d_str]["listhour"].copy(); h_data["walkdate"] = d_str; list_hour.append(h_data)
            # 历史日期强制任务成功，今日则看实际情况
            t_state = 1 if (d_str < today_str or summary["stepNumber"] > 6000) else 0
            list_recipe.append({
                "recipenumber": 9999, "task1state": t_state, "task2state": t_state, "task3state": t_state, 
                "task4state": t_state, "task5state": 2, "task6state": 2, "task7state": 2, "task8state": 2, "walkdate": d_str
            })

        payload = {
            "accessToken": self.token, "commond": "newUploadData",
            "dayPackage": str(self.last_day_id), "hourPackage": str(self.last_hour_id + 1),
            "deviceType": "TW726", "deviceserial": self.device_serial, "reqservicetype": "0", 
            "sequenceID": str(int(time.time())), "clientvison": "6.5.3",
            "listRecipeData": list_recipe, "listday": list_day, "listhour": list_hour
        }
        return payload, list_day[-1]

    def run(self):
        payload_body, today_summary = self.build_payload()
        post_data = {"commond": "pcUploadData", "ReqMessageBody": json.dumps(payload_body, separators=(',', ':'))}
        print(f"[*] 整合完毕！包含 {len(payload_body['listday'])} 天数据，今日累计: {today_summary['stepNumber']}")
        try:
            res = requests.post("http://sync.wanbu.com.cn/WanbuDataServer_NEW/PCPedUploadFlowsService", data=post_data, timeout=15)
            if '"resultCode":"0000"' in res.text:
                print("[+] 同步成功！")
                self.session["lastHourId"] = int(payload_body["hourPackage"])
                self.session["lastDayId"] = int(payload_body["dayPackage"])
                self.session["lastSyncDate"] = datetime.now().strftime("%Y%m%d") 
                with open("session.json", "w", encoding="utf-8") as f: json.dump(self.session, f, indent=4)
            else: print(f"[!] 服务器报错: {res.text}")
        except Exception as e: print(f"[!] 网络异常: {e}")

if __name__ == "__main__":
    if os.path.exists("session.json"):
        with open("session.json", "r", encoding="utf-8") as f: HumanGenerator(json.load(f)).run()

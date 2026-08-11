# Smart Pedometer Simulator & Auto-Sync


A Python-based automation tool for pedometer data synchronization and advanced human behavior simulation. This project is designed to generate highly realistic, physics-based step data and seamlessly sync it with health-tracking platforms.


## ✨ Features
* **Protocol Interception**: Utilizes `mitmproxy` to automatically intercept and safely block the original zero-step/empty data packets before they reach the server.
* **Behavioral Modeling**: Dynamically and randomly distributes steps across different hours of the day. Precisely controls walking cadence (e.g., 110-140 steps/min) to meet strict health-task algorithms.
* **Physics Simulation**: Intelligently differentiates between "dedicated walking tasks" and "casual daily movements." It dynamically calculates realistic ratios for effective steps, fast steps, and total walking duration.
* **State Persistence**: Features a built-in memory system to track your synchronization progress locally. Supports incremental data generation and multi-day batch uploads without overlapping or missing data.


## 🛠 Prerequisites
* Python 3.8 or higher
* Required packages: `requests`, `mitmproxy`, `python-dotenv`


Install the required dependencies via pip:
```bash
pip install requests mitmproxy python-dotenv
```


## 🚀 Quick Start / Usage Guide


The workflow consists of two main phases: **Data Capture (Interception)** and **Data Generation (Simulation)**.


### Step 1: Capture the Session Data
Run the interception script to capture the necessary authentication tokens and device parameters.


1. Execute the launcher script in your terminal:
   ```bash
   python start.py
   ```
2. The script will automatically configure your system's proxy settings.
3. Open your official pedometer PC client, connect your device, and click the **Sync** button.
4. The interceptor will block the original upload to protect your data integrity. Once you see `[SUCCESS] session.json extracted` in your terminal, press `Ctrl+C` to safely exit the interceptor.


### Step 2: Generate and Sync Data
Run the generator script to create realistic data based on the captured session and upload it to the server.


1. Ensure the `session.json` file is present in the same directory.
2. Execute the generator script:
   ```bash
   python generator.py
   ```
3. The script will dynamically generate today's step distribution based on the current time, merge it with previous days (if applicable), and submit the batch data to the server. 
4. Check your mobile app to verify the successfully synced data and completed tasks.


## 👥 多账户模式 (Multi-Account)

本工具支持多台计步器 / 多个账号同时管理，**每个设备（deviceserial）拥有完全独立的步数进度**。
由于 `accessToken` 约 3 天过期、而 `deviceserial` 是硬件永久序列号，因此以 **deviceserial 作为账户唯一主键**。

账户存储结构：

```
accounts/
  <设备序列号>/
    session.json            # 该设备最新凭证 + 进度 + 抓包时间(capturedAt)
    steps_db.json           # 该账户独立步数历史
    captured_history.json   # 抓包历史（临时，同步后自动归档）
    captured_history_*.bak  # 归档备份
```

### 添加 / 更新账户
1. 运行 `python start.py` 开启代理并抓包。
2. 用**该账号对应的计步器**点击同步一次。
3. 拦截器会自动按 `deviceserial` 归位到对应账户目录（新设备自动新建账户，已有设备自动更新 token）。

### 同步指定账户
```bash
python generator.py               # 交互式选择账户（有多个账户时）
python generator.py <设备序列号>   # 直接同步指定账户
```

### 全自动运行（所有账户）
计划任务或双击 `auto_run.bat` 会自动遍历 `accounts\` 目录下的**所有账户**，
逐个提交数据并微信推送，日志写入 `run_log.txt`。

> 💡 token 有效期约 3 天：运行时会根据 `capturedAt` 显示每个账户的 token 状态，
> 过期后请用对应设备重新执行 `start.py` 抓包续期。
> 想给账户起个便于识别的名字，可在 `accounts/<序列号>/session.json` 中添加 `"name": "张三"` 字段。


## ⚠️ Disclaimer
This project is intended for educational and research purposes only, specifically for understanding network protocol interception and behavioral data modeling. The author is not responsible for any account suspension, data loss, or violation of third-party Terms of Service resulting from the use of this tool. Please use it responsibly.
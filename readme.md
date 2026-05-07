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


## ⚠️ Disclaimer
This project is intended for educational and research purposes only, specifically for understanding network protocol interception and behavioral data modeling. The author is not responsible for any account suspension, data loss, or violation of third-party Terms of Service resulting from the use of this tool. Please use it responsibly.
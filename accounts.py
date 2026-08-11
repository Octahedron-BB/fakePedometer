"""
多账户账户库管理模块

每个计步器设备（deviceserial 永久不变）对应一个独立账户目录：
    accounts/<serial>/
        session.json              # 该设备最新凭证 + 进度 + 抓包时间
        steps_db.json             # 该账户独立步数进度
        captured_history.json     # 抓包历史（临时，阅后即焚）
        captured_history_*.bak    # 归档备份

token（accessToken）约 3 天过期，因此 capturedAt 用于提醒用户重新抓包；
而 deviceserial 是硬件永久序列号，作为账户唯一主键。
"""
import os
import json
import time
from datetime import datetime

ACCOUNTS_DIR = "accounts"
TOKEN_TTL_DAYS = 3


# ---------------------------------------------------------------- 路径

def account_dir(serial):
    """返回某设备的账户目录"""
    return os.path.join(ACCOUNTS_DIR, serial)


def session_path(serial):
    return os.path.join(account_dir(serial), "session.json")


def db_path(serial):
    return os.path.join(account_dir(serial), "steps_db.json")


def capture_path(serial):
    return os.path.join(account_dir(serial), "captured_history.json")


def ensure_account(serial):
    d = account_dir(serial)
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------- session

def session_exists(serial):
    return os.path.exists(session_path(serial))


def load_session(serial):
    p = session_path(serial)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_session(serial, session):
    ensure_account(serial)
    with open(session_path(serial), "w", encoding="utf-8") as f:
        json.dump(session, f, indent=4)


# ---------------------------------------------------------------- 步数进度

def load_db(serial):
    p = db_path(serial)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_db(serial, db):
    ensure_account(serial)
    with open(db_path(serial), "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)


# ---------------------------------------------------------------- 抓包历史

def load_capture(serial):
    p = capture_path(serial)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_capture(serial, data):
    ensure_account(serial)
    with open(capture_path(serial), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def archive_capture(serial):
    """把抓包文件归档，防止重复读取；返回归档文件名或 None"""
    p = capture_path(serial)
    if os.path.exists(p):
        bak = os.path.join(account_dir(serial), f"captured_history_{int(time.time())}.bak")
        os.rename(p, bak)
        return bak
    return None


# ---------------------------------------------------------------- 账户枚举

def list_accounts():
    """列出所有账户，返回 [{serial, name, token_age_days}]"""
    result = []
    if not os.path.isdir(ACCOUNTS_DIR):
        return result
    for name in sorted(os.listdir(ACCOUNTS_DIR)):
        if not os.path.isdir(account_dir(name)) or not session_exists(name):
            continue
        session = load_session(name) or {}
        captured_at = session.get("capturedAt")
        age = None
        if captured_at:
            try:
                ct = datetime.fromisoformat(captured_at)
                age = (datetime.now() - ct).total_seconds() / 86400.0
            except ValueError:
                age = None
        result.append({
            "serial": name,
            "name": session.get("name", ""),
            "token_age_days": age,
        })
    return result


def token_status(age_days):
    """根据 token 已存活天数返回状态字符串"""
    if age_days is None:
        return "未知时效"
    if age_days > TOKEN_TTL_DAYS:
        return f"⚠️ token 已过期({age_days:.1f}天)"
    return f"✓ token 有效({age_days:.1f}天)"


# ---------------------------------------------------------------- 旧数据迁移

def migrate_legacy():
    """一次性迁移旧的根目录单账户数据到账户目录。

    仅当根目录存在旧 session.json 且还没有任何账户目录时执行，
    返回迁移出的 deviceserial，否则返回 None。
    """
    legacy_session = "session.json"
    legacy_db = "my_steps_db.json"
    legacy_capture = "captured_history.json"

    if not os.path.exists(legacy_session) or os.path.exists(ACCOUNTS_DIR):
        return None

    try:
        with open(legacy_session, "r", encoding="utf-8") as f:
            session = json.load(f)
    except Exception:
        return None

    serial = session.get("deviceSerial")
    if not serial:
        return None

    ensure_account(serial)
    os.rename(legacy_session, session_path(serial))
    if os.path.exists(legacy_db):
        os.rename(legacy_db, db_path(serial))
    if os.path.exists(legacy_capture):
        os.rename(legacy_capture, capture_path(serial))
    print(f"[+] 已把旧单账户数据迁移到账户: {serial}")
    return serial

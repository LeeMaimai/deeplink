"""
完整流程测试：模拟从网页访问到注册的全链路

运行: python3 test_full_flow.py
前提: server/app.py 已启动在 localhost:5050
"""

import requests
import time
import json

BASE = "http://localhost:5050"
NOW = time.time()


def sep(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def visit(data):
    r = requests.post(f"{BASE}/api/track/visit", json=data).json()
    print(f"  [Visit #{r['visit_id']}] recorded")
    return r


def click(data):
    r = requests.post(f"{BASE}/api/track/click", json=data).json()
    print(f"  [Click #{r['click_id']}] recorded")
    return r


def install(data):
    r = requests.post(f"{BASE}/api/track/install", json=data).json()
    m = r["match"]
    status = f"MATCHED Click #{m['click_id']} (score: {m['score']})" if m["matched"] else f"NO MATCH (best: {m['score']})"
    print(f"  [Install #{r['install_id']}] {status}")
    if m["matched"]:
        print(f"    → channel={m['channel']}, campaign={m['campaign']}")
    for d in m["details"]:
        print(f"      {d}")
    return r


def register(data):
    r = requests.post(f"{BASE}/api/track/register", json=data).json()
    print(f"  [Register #{r['register_id']}] channel={r.get('channel', 'none')}")
    return r


def stats():
    r = requests.get(f"{BASE}/api/stats").json()
    f = r["funnel"]
    m = r["matching"]
    print(f"\n  Funnel:  {f['visits']} visits → {f['clicks']} clicks → {f['installs']} installs → {f['registers']} registers")
    print(f"  Match:   {m['matched']} matched, {m['unmatched']} unmatched, rate={m['match_rate']}")
    if r["by_channel"]:
        print(f"  Channels:")
        for ch, s in r["by_channel"].items():
            print(f"    {ch}: {s['visits']}v / {s['clicks']}c / {s['installs']}i / {s['registers']}r")


# ============================================================
# 清空数据
# ============================================================
requests.post(f"{BASE}/api/reset")


# ============================================================
sep("USER A: Twitter → iOS App Store → Install → Register")
# ============================================================

print("\n1. User A sees a tweet, clicks link to onekey.so/download?channel=twitter&campaign=spring2026")
visit({
    "ip": "203.0.113.50",
    "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15",
    "screen": "1206x2622",
    "language": "zh-CN",
    "timezone": "Asia/Shanghai",
    "referrer": "https://twitter.com/OneKeyHQ/status/123456",
    "page_url": "https://onekey.so/download?channel=twitter&campaign=spring2026",
    "channel": "twitter",
    "campaign": "spring2026",
    "session_id": "sess_userA",
    "time": NOW - 600,
})

print("\n2. User A clicks 'App Store' download button")
click({
    "ip": "203.0.113.50",
    "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15",
    "screen": "1206x2622",
    "language": "zh-CN",
    "timezone": "Asia/Shanghai",
    "platform": "ios",
    "channel": "twitter",
    "campaign": "spring2026",
    "session_id": "sess_userA",
    "time": NOW - 590,
})

print("\n3. User A installs from App Store and opens OneKey for the first time")
install({
    "ip": "203.0.113.50",
    "screen": "1206x2622",
    "language": "zh",
    "timezone": "Asia/Shanghai",
    "os": "iOS",
    "os_version": "18.3",
    "model": "iPhone",
    "platform": "ios",
    "app_version": "5.10.0",
    "instance_id": "inst_userA_abc123",
    "time": NOW - 300,
})

print("\n4. User A completes onboarding and creates a wallet (register)")
register({
    "instance_id": "inst_userA_abc123",
    "time": NOW - 100,
})


# ============================================================
sep("USER B: Google Ads → Android Google Play → Install (IP changed)")
# ============================================================

print("\n1. User B clicks Google ad, lands on onekey.so/download?channel=google&campaign=sem_q1")
visit({
    "ip": "120.78.10.50",
    "ua": "Mozilla/5.0 (Linux; Android 15; Pixel 8 Build/AP3A) AppleWebKit/537.36",
    "screen": "1080x2400",
    "language": "en-US",
    "timezone": "America/Los_Angeles",
    "referrer": "https://www.google.com/",
    "page_url": "https://onekey.so/download?channel=google&campaign=sem_q1",
    "channel": "google",
    "campaign": "sem_q1",
    "session_id": "sess_userB",
    "time": NOW - 7200,
})

print("\n2. User B clicks 'Google Play' download button")
click({
    "ip": "120.78.10.50",
    "ua": "Mozilla/5.0 (Linux; Android 15; Pixel 8 Build/AP3A) AppleWebKit/537.36",
    "screen": "1080x2400",
    "language": "en-US",
    "timezone": "America/Los_Angeles",
    "platform": "android",
    "channel": "google",
    "campaign": "sem_q1",
    "session_id": "sess_userB",
    "time": NOW - 7190,
})

print("\n3. User B installs from Play Store, but now on different WiFi (IP changed)")
install({
    "ip": "45.33.88.100",  # different IP!
    "screen": "1080x2400",
    "language": "en",
    "timezone": "America/Los_Angeles",
    "os": "Android",
    "os_version": "15",
    "model": "Pixel 8",
    "platform": "android",
    "app_version": "5.10.0",
    "instance_id": "inst_userB_def456",
    "time": NOW - 3600,
})

print("\n4. User B registers")
register({
    "instance_id": "inst_userB_def456",
    "time": NOW - 3500,
})


# ============================================================
sep("USER C: Telegram → Desktop (direct download)")
# ============================================================

print("\n1. User C clicks Telegram link to onekey.so/download?channel=telegram&campaign=airdrop")
visit({
    "ip": "210.148.100.5",
    "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "screen": "3840x2160",
    "language": "ja",
    "timezone": "Asia/Tokyo",
    "referrer": "https://t.me/OneKeyHQ",
    "page_url": "https://onekey.so/download?channel=telegram&campaign=airdrop",
    "channel": "telegram",
    "campaign": "airdrop",
    "session_id": "sess_userC",
    "time": NOW - 1800,
})

print("\n2. User C clicks 'Desktop App' download button")
click({
    "ip": "210.148.100.5",
    "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "screen": "3840x2160",
    "language": "ja",
    "timezone": "Asia/Tokyo",
    "platform": "desktop",
    "channel": "telegram",
    "campaign": "airdrop",
    "session_id": "sess_userC",
    "time": NOW - 1790,
})

print("\n3. User C opens Desktop app for the first time")
install({
    "ip": "210.148.100.5",
    "screen": "3840x2160",
    "language": "ja",
    "timezone": "Asia/Tokyo",
    "os": "macOS",
    "os_version": "15.3",
    "model": "Mac",
    "platform": "desktop",
    "app_version": "5.10.0",
    "instance_id": "inst_userC_ghi789",
    "time": NOW - 900,
})


# ============================================================
sep("USER D: Organic install (no prior click)")
# ============================================================

print("\n1. User D searches App Store directly and installs OneKey")
install({
    "ip": "180.150.60.70",
    "screen": "1179x2556",
    "language": "ko",
    "timezone": "Asia/Seoul",
    "os": "iOS",
    "os_version": "18.3",
    "model": "iPhone",
    "platform": "ios",
    "app_version": "5.10.0",
    "instance_id": "inst_userD_organic",
    "time": NOW - 200,
})

print("\n2. User D registers")
register({
    "instance_id": "inst_userD_organic",
    "time": NOW - 100,
})


# ============================================================
sep("FINAL STATS")
# ============================================================
stats()

print(f"\n  Open http://localhost:5050/dashboard to see full visual results.\n")

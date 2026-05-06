"""
Attribution Service

API:
  POST /api/track/visit    事件1：访问网页
  POST /api/track/click    事件2：点击下载
  POST /api/track/install  事件3：首次打开App（触发匹配）
  POST /api/track/register 事件4：注册
  GET  /api/stats          统计概览
  GET  /api/records        全部记录明细
  POST /api/reset          清空数据

Pages:
  GET /                    测试落地页
  GET /dashboard           匹配结果面板
"""

from flask import Flask, request, jsonify, send_from_directory
from matcher import find_best_match
import time
import os
import uuid

app = Flask(__name__)

# ---------- 存储 ----------
visits = []
clicks = []
installs = []
registers = []


def get_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def base_fingerprint(data: dict) -> dict:
    """提取公共指纹字段"""
    return {
        "ip": data.get("ip") or get_ip(),
        "ua": data.get("ua") or request.headers.get("User-Agent", ""),
        "screen": data.get("screen", ""),
        "language": data.get("language", ""),
        "timezone": data.get("timezone", ""),
        "os": data.get("os", ""),
        "os_version": data.get("os_version", ""),
        "model": data.get("model", ""),
    }


# ============================================================
# 事件 1：访问网页
# ============================================================
@app.route("/api/track/visit", methods=["POST"])
def track_visit():
    data = request.json or {}
    record = {
        "id": len(visits) + 1,
        **base_fingerprint(data),
        "session_id": data.get("session_id", ""),
        "referrer": data.get("referrer", ""),
        "page_url": data.get("page_url", ""),
        "channel": data.get("channel", ""),
        "campaign": data.get("campaign", ""),
        "utm_source": data.get("utm_source", ""),
        "utm_medium": data.get("utm_medium", ""),
        "time": data.get("time") or time.time(),
    }
    visits.append(record)
    return jsonify({"ok": True, "visit_id": record["id"]})


# ============================================================
# 事件 2：点击下载
# ============================================================
@app.route("/api/track/click", methods=["POST"])
def track_click():
    data = request.json or {}
    record = {
        "id": len(clicks) + 1,
        **base_fingerprint(data),
        "session_id": data.get("session_id", ""),
        "referrer": data.get("referrer", ""),
        "page_url": data.get("page_url", ""),
        "platform": data.get("platform", ""),  # ios / android / desktop / extension
        "channel": data.get("channel", ""),
        "campaign": data.get("campaign", ""),
        "utm_source": data.get("utm_source", ""),
        "utm_medium": data.get("utm_medium", ""),
        "custom_params": data.get("custom_params", {}),
        "time": data.get("time") or time.time(),
        "matched_install_id": None,
    }
    clicks.append(record)
    return jsonify({"ok": True, "click_id": record["id"]})


# ============================================================
# 事件 3：首次打开 App（触发匹配）
# ============================================================
@app.route("/api/track/install", methods=["POST"])
def track_install():
    data = request.json or {}
    record = {
        "id": len(installs) + 1,
        **base_fingerprint(data),
        "instance_id": data.get("instance_id", ""),
        "app_version": data.get("app_version", ""),
        "platform": data.get("platform", ""),
        "time": data.get("time") or time.time(),
    }

    # 执行匹配
    result = find_best_match(record, clicks)
    record["match"] = result

    if result["matched"]:
        record["matched_click_id"] = result["click_id"]
        record["channel"] = result["channel"]
        record["campaign"] = result["campaign"]
        record["custom_params"] = result["custom_params"]
        # 更新点击记录的反向关联
        for c in clicks:
            if c["id"] == result["click_id"]:
                c["matched_install_id"] = record["id"]
    else:
        record["matched_click_id"] = None
        record["channel"] = ""
        record["campaign"] = ""
        record["custom_params"] = {}

    installs.append(record)

    return jsonify({
        "ok": True,
        "install_id": record["id"],
        "match": result,
    })


# ============================================================
# 事件 4：注册
# ============================================================
@app.route("/api/track/register", methods=["POST"])
def track_register():
    data = request.json or {}
    instance_id = data.get("instance_id", "")

    # 通过 instance_id 找到对应的安装记录
    linked_install = None
    for inst in installs:
        if inst["instance_id"] == instance_id:
            linked_install = inst
            break

    record = {
        "id": len(registers) + 1,
        "instance_id": instance_id,
        "install_id": linked_install["id"] if linked_install else None,
        "channel": linked_install["channel"] if linked_install else "",
        "campaign": linked_install["campaign"] if linked_install else "",
        "time": data.get("time") or time.time(),
    }
    registers.append(record)

    return jsonify({"ok": True, "register_id": record["id"], "channel": record["channel"]})


# ============================================================
# 统计 & 查询
# ============================================================
@app.route("/api/stats")
def stats():
    matched = sum(1 for i in installs if i.get("matched_click_id"))
    unmatched = len(installs) - matched

    # 按渠道统计
    channel_stats = {}
    for inst in installs:
        ch = inst.get("channel") or "(organic)"
        if ch not in channel_stats:
            channel_stats[ch] = {"visits": 0, "clicks": 0, "installs": 0, "registers": 0}
        channel_stats[ch]["installs"] += 1

    for v in visits:
        ch = v.get("channel") or "(organic)"
        if ch not in channel_stats:
            channel_stats[ch] = {"visits": 0, "clicks": 0, "installs": 0, "registers": 0}
        channel_stats[ch]["visits"] += 1

    for c in clicks:
        ch = c.get("channel") or "(organic)"
        if ch not in channel_stats:
            channel_stats[ch] = {"visits": 0, "clicks": 0, "installs": 0, "registers": 0}
        channel_stats[ch]["clicks"] += 1

    for r in registers:
        ch = r.get("channel") or "(organic)"
        if ch not in channel_stats:
            channel_stats[ch] = {"visits": 0, "clicks": 0, "installs": 0, "registers": 0}
        channel_stats[ch]["registers"] += 1

    return jsonify({
        "funnel": {
            "visits": len(visits),
            "clicks": len(clicks),
            "installs": len(installs),
            "registers": len(registers),
        },
        "matching": {
            "matched": matched,
            "unmatched": unmatched,
            "match_rate": f"{matched/len(installs)*100:.1f}%" if installs else "N/A",
        },
        "by_channel": channel_stats,
    })


@app.route("/api/records")
def records():
    return jsonify({
        "visits": visits,
        "clicks": clicks,
        "installs": installs,
        "registers": registers,
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    visits.clear()
    clicks.clear()
    installs.clear()
    registers.clear()
    return jsonify({"ok": True})


# ============================================================
# 页面
# ============================================================
DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "demo")
SDK_DIR = os.path.join(os.path.dirname(__file__), "..", "web-sdk")


@app.route("/")
def landing():
    return send_from_directory(DEMO_DIR, "landing.html")


@app.route("/dashboard")
def dashboard():
    return send_from_directory(DEMO_DIR, "dashboard.html")


@app.route("/app-simulator")
def app_simulator():
    return send_from_directory(DEMO_DIR, "app-simulator.html")


@app.route("/sdk/attribution.js")
def serve_sdk():
    return send_from_directory(SDK_DIR, "attribution.js", mimetype="application/javascript")


if __name__ == "__main__":
    print("Attribution Service running at http://localhost:5050")
    print("Landing page: http://localhost:5050/?channel=twitter&campaign=test01")
    print("Dashboard:    http://localhost:5050/dashboard")
    app.run(host="0.0.0.0", port=5050, debug=True)

"""
归因匹配算法

匹配规则：
- IP 完全匹配:        40 分
- 屏幕分辨率匹配:      20 分
- OS + 版本匹配:       15 分（OS 5 + 版本 10）
- 设备型号匹配:        5 分
- 语言匹配:            5 分
- 时区匹配:            5 分
- 时间衰减:            24 小时内线性衰减，最多扣 10 分
满分 90，阈值 50
"""

import re
import time


MATCH_THRESHOLD = 50
MATCH_WINDOW_HOURS = 24


def parse_device_from_ua(ua: str) -> dict:
    """从 User-Agent 提取设备信息"""
    info = {"os": "", "os_version": "", "device": ""}
    if not ua:
        return info

    # iOS
    m = re.search(r"(iPhone|iPad|iPod)", ua)
    if m:
        info["device"] = m.group(1)
        info["os"] = "iOS"
        v = re.search(r"OS (\d+[_.]\d+)", ua)
        if v:
            info["os_version"] = v.group(1).replace("_", ".")
        return info

    # Android
    m = re.search(r"Android\s*([\d.]+)", ua)
    if m:
        info["os"] = "Android"
        info["os_version"] = m.group(1)
        d = re.search(r";\s*([^;)]+)\s*Build", ua)
        if d:
            info["device"] = d.group(1).strip()
        return info

    # macOS
    m = re.search(r"Mac OS X (\d+[_.]\d+)", ua)
    if m:
        info["os"] = "macOS"
        info["os_version"] = m.group(1).replace("_", ".")
        info["device"] = "Mac"
        return info

    # Windows
    m = re.search(r"Windows NT ([\d.]+)", ua)
    if m:
        info["os"] = "Windows"
        info["os_version"] = m.group(1)
        info["device"] = "PC"

    return info


def normalize_language(lang: str) -> str:
    """统一语言码：zh-CN, zh-Hans → zh"""
    return (lang or "")[:2].lower()


def calculate_score(click: dict, install: dict) -> tuple[float, list[str]]:
    """
    计算一次点击和一次安装之间的匹配分数。
    返回 (score, details)
    """
    score = 0.0
    details = []

    # 1. IP（40 分）
    if click.get("ip") and click["ip"] == install.get("ip"):
        score += 40
        details.append(f"IP match ({click['ip']}): +40")
    else:
        details.append(f"IP mismatch ({click.get('ip')} vs {install.get('ip')}): +0")

    # 2. 屏幕分辨率（20 分）
    c_screen = click.get("screen", "")
    i_screen = install.get("screen", "")
    if c_screen and c_screen == i_screen:
        score += 20
        details.append(f"Screen match ({c_screen}): +20")
    elif c_screen and i_screen:
        details.append(f"Screen mismatch ({c_screen} vs {i_screen}): +0")

    # 3. OS + 版本（5 + 10 = 15 分）
    c_ua = parse_device_from_ua(click.get("ua"))
    i_ua = parse_device_from_ua(install.get("ua"))

    c_os = click.get("os") or c_ua["os"]
    c_os_ver = click.get("os_version") or c_ua["os_version"]
    i_os = install.get("os") or i_ua["os"]
    i_os_ver = install.get("os_version") or i_ua["os_version"]

    if c_os and c_os == i_os:
        score += 5
        details.append(f"OS match ({c_os}): +5")
        if c_os_ver and c_os_ver == i_os_ver:
            score += 10
            details.append(f"OS version match ({c_os_ver}): +10")
        else:
            details.append(f"OS version mismatch ({c_os_ver} vs {i_os_ver}): +0")
    else:
        details.append(f"OS mismatch ({c_os} vs {i_os}): +0")

    # 4. 设备型号（5 分）
    c_model = click.get("model") or c_ua["device"]
    i_model = install.get("model") or i_ua["device"]
    if c_model and c_model == i_model:
        score += 5
        details.append(f"Model match ({c_model}): +5")

    # 5. 语言（5 分）
    c_lang = normalize_language(click.get("language"))
    i_lang = normalize_language(install.get("language"))
    if c_lang and c_lang == i_lang:
        score += 5
        details.append(f"Language match ({c_lang}): +5")

    # 6. 时区（5 分）
    if click.get("timezone") and click["timezone"] == install.get("timezone"):
        score += 5
        details.append(f"Timezone match ({click['timezone']}): +5")

    # 7. 时间衰减（最多 -10 分）
    c_time = click.get("time", 0)
    i_time = install.get("time", 0)
    hours_diff = (i_time - c_time) / 3600

    if hours_diff < 0:
        score = 0
        details.append("Install before click: score → 0")
    elif hours_diff <= 1:
        details.append(f"Time gap: {hours_diff:.1f}h, no decay")
    elif hours_diff <= MATCH_WINDOW_HOURS:
        decay = (hours_diff / MATCH_WINDOW_HOURS) * 10
        score -= decay
        details.append(f"Time gap: {hours_diff:.1f}h, decay: -{decay:.1f}")
    else:
        score = 0
        details.append(f"Time gap: {hours_diff:.1f}h, over {MATCH_WINDOW_HOURS}h window: score → 0")

    return round(max(score, 0), 1), details


def find_best_match(install: dict, clicks: list[dict]) -> dict:
    """
    为一次安装在所有点击记录中找到最佳匹配。
    返回匹配结果。
    """
    best = None
    best_score = 0
    best_details = []
    candidates = []

    for click in clicks:
        s, d = calculate_score(click, install)
        candidates.append({
            "click_id": click["id"],
            "score": s,
            "details": d,
            "channel": click.get("channel", ""),
            "campaign": click.get("campaign", ""),
        })
        if s > best_score:
            best_score = s
            best = click
            best_details = d

    matched = best_score >= MATCH_THRESHOLD

    return {
        "matched": matched,
        "score": best_score,
        "threshold": MATCH_THRESHOLD,
        "click_id": best["id"] if best and matched else None,
        "channel": best.get("channel", "") if best and matched else "",
        "campaign": best.get("campaign", "") if best and matched else "",
        "custom_params": best.get("custom_params", {}) if best and matched else {},
        "details": best_details,
        "candidates": sorted(candidates, key=lambda x: -x["score"])[:10],
    }

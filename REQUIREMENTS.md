# 广告归因 / Deeplink 模糊匹配 需求文档

## 背景
即将开始投放广告，需要追踪完整漏斗：**广告 → 带 UTM 官网 → 点击下载 → App 首启 → 注册**。核心难点是把"官网点了下载的用户"和"App 新启动的用户"匹配起来（App Store / Play 安装链路无法透传参数，必须靠指纹模糊匹配），用于分析每个渠道的真实用户行为，优化投放 ROI。

## 为什么自建
第三方方案要么按点击付费，月成本几千 U；要么便宜但强绑一堆不需要的工具。我们需求很纯：**仅做官网点击和 App 用户的匹配**。

## 数据流
4 个埋点事件，串成一个用户的完整链路：

| 事件 | 触发时机 | 关键字段 |
|---|---|---|
| `visit` | 落地页加载（自动） | UTM、referrer、设备指纹、session_id |
| `click` | 用户点下载按钮 | platform (ios/android/desktop)、UTM、指纹 |
| `install` | App 首次启动 | instance_id、指纹（**触发匹配**） |
| `register` | 注册完成 | instance_id（用来回链 install） |

## 匹配算法 v1

这套打分算法在行业里称为 **Fingerprint Matching / Probabilistic Attribution（指纹匹配 / 概率归因）**，是 AppsFlyer、Branch、Adjust、Singular 等主流 MMP（Mobile Measurement Partner）在缺少设备 ID 时通用的归因方式，**并非自创**。

**信号选择**：MMP 在 click 时记录 IP、UA、OS 版本、机型、屏幕尺寸、时区、locale 等设备指纹，App 首启时再次采集，比对相似度。我们选的 7 个维度是这套通用信号集的子集（参考 [Branch — Deferred Deep Linking with Device Snapshotting](https://www.branch.io/resources/blog/deferred-deep-linking-with-device-snapshotting/)、[AppsFlyer — What is Probabilistic Modeling](https://www.appsflyer.com/glossary/probabilistic-modeling/)）。

**权重逻辑**：信号区分度越高权重越大。IP 在短时间窗内独立性最强（同 IP + 同时段 + 同型号机的碰撞率极低），故 40 分主导；屏幕分辨率次之 20 分；OS+版本组合 15 分；机型/语言/时区作为辅助验证各 5 分。这种"多信号加权 + 阈值判定"的形态和 [Mediasmart — Fingerprinting and Attribution](https://blog.mediasmart.io/fingerprinting-and-attribution-shining-a-light-in-the-dark) 描述一致。

**24h 窗口**：Singular 等 MMP 将概率匹配的默认 lookback window 设为 24h，因为设备指纹的可识别性会随时间指数衰减（[Singular — Probabilistic Attribution FAQ](https://support.singular.net/hc/en-us/articles/360002290752-Probabilistic-Attribution-FAQ)）。我们采用相同的 24h 窗口，1h–24h 间线性衰减分值。

---

install 触发时，遍历所有 click，按以下维度打分，取最高分：

| 维度 | 分值 |
|---|---|
| IP 匹配 | 40 |
| 屏幕分辨率 | 20 |
| OS + 版本 | 5 + 10 |
| 设备型号 | 5 |
| 语言 | 5 |
| 时区 | 5 |
| 时间衰减 | -10 max |

总分 90，**阈值 ≥ 50 视为命中**。

时间衰减规则：≤1h 不衰减；1–24h 线性衰减最多 -10；>24h 或 install 时间早于 click → 直接 0。

## 后台需展示
- 漏斗：visits → clicks → installs → registers
- 匹配率 + 未匹配明细
- 按 channel / campaign 分组统计
- 每条 install 的打分明细（方便调阈值）

## 迭代说明
v1 是先跑通的方案，后续根据真实数据准确率可调整：权重、阈值、新增维度（运营商、字体列表、Canvas 指纹），必要时换成 ML。

## 参考实现
完整可跑的 demo 仓库（Flask 后端 + Web SDK + iOS/Android SDK + 模拟器 + 看板 + 端到端测试），**仅作为思路和算法参考**，实际落地需根据真实场景做工程化处理（数据持久化、并发、安全、风控等）：

👉 https://github.com/LeeMaimai/deeplink

包含：
- `server/matcher.py` — 匹配算法实现
- `server/app.py` — 4 个接口 + 统计
- `web-sdk/attribution.js` — 网页 SDK
- `app-sdk/AttributionSDK.{swift,kt}` — 双端 SDK
- `demo/dashboard.html` — 看板
- `test/test_full_flow.py` — 4 个用户场景端到端测试

/**
 * OneKey Attribution iOS SDK
 *
 * 接入方式：
 * 1. 将此文件加入项目
 * 2. 在 App 首次启动时调用 OnekeyAttribution.trackInstall()
 * 3. 在用户注册成功时调用 OnekeyAttribution.trackRegister()
 */

import UIKit

class OnekeyAttribution {

    // TODO: 替换为你的归因服务地址
    static let server = "https://your-attribution-server.com"

    private static let trackedKey = "onekey_attribution_tracked"
    private static let channelKey = "onekey_attribution_channel"
    private static let campaignKey = "onekey_attribution_campaign"
    private static let paramsKey = "onekey_attribution_params"

    // MARK: - 事件3：首次打开App

    /// 在 App 首次启动时调用（建议在 AppDelegate 或 onboarding 流程开始前）
    /// 只会执行一次，重复调用会被忽略
    static func trackInstall(instanceId: String, completion: ((Bool, String?, String?) -> Void)? = nil) {
        guard !UserDefaults.standard.bool(forKey: trackedKey) else {
            let ch = UserDefaults.standard.string(forKey: channelKey)
            let ca = UserDefaults.standard.string(forKey: campaignKey)
            completion?(ch != nil, ch, ca)
            return
        }

        let fingerprint = collectFingerprint(instanceId: instanceId)

        post(endpoint: "/api/track/install", body: fingerprint) { data in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let match = json["match"] as? [String: Any] else {
                completion?(false, nil, nil)
                return
            }

            let matched = match["matched"] as? Bool ?? false
            let channel = match["channel"] as? String
            let campaign = match["campaign"] as? String
            let score = match["score"] as? Double ?? 0

            // 持久化结果
            UserDefaults.standard.set(true, forKey: trackedKey)
            if matched {
                UserDefaults.standard.set(channel, forKey: channelKey)
                UserDefaults.standard.set(campaign, forKey: campaignKey)
                if let params = match["custom_params"] as? [String: Any],
                   let paramsData = try? JSONSerialization.data(withJSONObject: params) {
                    UserDefaults.standard.set(paramsData, forKey: paramsKey)
                }
            }

            print("[Attribution] matched=\(matched), score=\(score), channel=\(channel ?? "none"), campaign=\(campaign ?? "none")")
            completion?(matched, channel, campaign)
        }
    }

    // MARK: - 事件4：注册

    /// 在用户注册成功后调用
    static func trackRegister(instanceId: String) {
        let body: [String: Any] = [
            "instance_id": instanceId,
        ]
        post(endpoint: "/api/track/register", body: body, completion: nil)
    }

    // MARK: - 读取归因结果

    /// 获取已保存的渠道信息（匹配成功后可用）
    static var channel: String? {
        UserDefaults.standard.string(forKey: channelKey)
    }

    static var campaign: String? {
        UserDefaults.standard.string(forKey: campaignKey)
    }

    // MARK: - 内部方法

    private static func collectFingerprint(instanceId: String) -> [String: Any] {
        let screen = UIScreen.main.nativeBounds
        return [
            "screen": "\(Int(screen.width))x\(Int(screen.height))",
            "language": Locale.current.language.languageCode?.identifier ?? "",
            "timezone": TimeZone.current.identifier,
            "os": "iOS",
            "os_version": UIDevice.current.systemVersion,
            "model": UIDevice.current.model,
            "app_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "",
            "platform": "ios",
            "instance_id": instanceId,
        ]
    }

    private static func post(endpoint: String, body: [String: Any], completion: ((Data?) -> Void)?) {
        guard let url = URL(string: server + endpoint) else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 10
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: req) { data, _, error in
            if let error = error {
                print("[Attribution] Error: \(error.localizedDescription)")
            }
            completion?(data)
        }.resume()
    }
}

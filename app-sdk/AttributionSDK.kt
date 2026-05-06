/**
 * OneKey Attribution Android SDK
 *
 * 接入方式：
 * 1. 将此文件加入项目
 * 2. 在 App 首次启动时调用 OnekeyAttribution.trackInstall()
 * 3. 在用户注册成功时调用 OnekeyAttribution.trackRegister()
 */

package com.onekey.attribution

import android.content.Context
import android.content.res.Resources
import android.os.Build
import android.webkit.WebSettings
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.TimeZone
import kotlin.concurrent.thread

object OnekeyAttribution {

    // TODO: 替换为你的归因服务地址
    var server = "https://your-attribution-server.com"

    private const val PREFS_NAME = "onekey_attribution"
    private const val KEY_TRACKED = "tracked"
    private const val KEY_CHANNEL = "channel"
    private const val KEY_CAMPAIGN = "campaign"

    /**
     * 事件3：首次打开App
     * 在 Application.onCreate 或首次进入主界面时调用
     */
    fun trackInstall(
        context: Context,
        instanceId: String,
        callback: ((matched: Boolean, channel: String?, campaign: String?) -> Unit)? = null
    ) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        if (prefs.getBoolean(KEY_TRACKED, false)) {
            val ch = prefs.getString(KEY_CHANNEL, null)
            val ca = prefs.getString(KEY_CAMPAIGN, null)
            callback?.invoke(ch != null, ch, ca)
            return
        }

        val fingerprint = collectFingerprint(context, instanceId)

        thread {
            try {
                val result = post("/api/track/install", fingerprint)
                val match = result?.optJSONObject("match")
                val matched = match?.optBoolean("matched") ?: false
                val channel = match?.optString("channel", null)
                val campaign = match?.optString("campaign", null)

                prefs.edit().apply {
                    putBoolean(KEY_TRACKED, true)
                    if (matched) {
                        putString(KEY_CHANNEL, channel)
                        putString(KEY_CAMPAIGN, campaign)
                    }
                    apply()
                }

                callback?.invoke(matched, channel, campaign)
            } catch (e: Exception) {
                e.printStackTrace()
                callback?.invoke(false, null, null)
            }
        }
    }

    /**
     * 事件4：注册
     */
    fun trackRegister(context: Context, instanceId: String) {
        val body = JSONObject().apply {
            put("instance_id", instanceId)
        }
        thread {
            try { post("/api/track/register", body) } catch (_: Exception) {}
        }
    }

    /**
     * 获取已保存的渠道
     */
    fun getChannel(context: Context): String? {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_CHANNEL, null)
    }

    // ---------- 内部方法 ----------

    private fun collectFingerprint(context: Context, instanceId: String): JSONObject {
        val dm = Resources.getSystem().displayMetrics
        return JSONObject().apply {
            put("screen", "${dm.widthPixels}x${dm.heightPixels}")
            put("language", Locale.getDefault().language)
            put("timezone", TimeZone.getDefault().id)
            put("os", "Android")
            put("os_version", Build.VERSION.RELEASE)
            put("model", Build.MODEL)
            put("app_version", try {
                context.packageManager.getPackageInfo(context.packageName, 0).versionName
            } catch (_: Exception) { "" })
            put("platform", "android")
            put("instance_id", instanceId)
        }
    }

    private fun post(endpoint: String, body: JSONObject): JSONObject? {
        val conn = URL(server + endpoint).openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.setRequestProperty("Content-Type", "application/json")
        conn.connectTimeout = 10000
        conn.doOutput = true
        conn.outputStream.write(body.toString().toByteArray())
        val response = conn.inputStream.bufferedReader().readText()
        conn.disconnect()
        return JSONObject(response)
    }
}

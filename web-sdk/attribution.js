/**
 * Attribution Web SDK
 *
 * 用法:
 *   <script src="/sdk/attribution.js" data-server="http://localhost:5050"></script>
 *
 *   // 页面加载时自动触发 visit 事件
 *   // 手动触发 click 事件:
 *   AttributionSDK.trackClick({ platform: "ios" });
 */

(function () {
  "use strict";

  var SERVER = "";
  var SESSION_KEY = "attr_session";
  var sessionId = "";

  // ---------- 工具函数 ----------

  function generateSessionId() {
    return "s_" + Math.random().toString(36).substr(2, 12) + "_" + Date.now();
  }

  function getSession() {
    try {
      var sid = sessionStorage.getItem(SESSION_KEY);
      if (!sid) {
        sid = generateSessionId();
        sessionStorage.setItem(SESSION_KEY, sid);
      }
      return sid;
    } catch (e) {
      return generateSessionId();
    }
  }

  function parseUrlParams() {
    var params = {};
    var search = window.location.search.substring(1);
    if (!search) return params;
    search.split("&").forEach(function (pair) {
      var kv = pair.split("=");
      if (kv[0]) params[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    });
    return params;
  }

  function getFingerprint() {
    var dpr = window.devicePixelRatio || 1;
    return {
      ua: navigator.userAgent,
      screen: Math.round(screen.width * dpr) + "x" + Math.round(screen.height * dpr),
      language: navigator.language || "",
      timezone: (function () {
        try { return Intl.DateTimeFormat().resolvedOptions().timeZone; }
        catch (e) { return ""; }
      })(),
    };
  }

  function post(endpoint, data, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", SERVER + endpoint, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4 && callback) {
        try { callback(JSON.parse(xhr.responseText)); }
        catch (e) { callback(null); }
      }
    };
    xhr.send(JSON.stringify(data));
  }

  // ---------- 初始化 ----------

  function init() {
    // 从 script 标签读取 server 地址
    var scripts = document.getElementsByTagName("script");
    for (var i = 0; i < scripts.length; i++) {
      var s = scripts[i];
      if (s.src && s.src.indexOf("attribution.js") !== -1) {
        SERVER = s.getAttribute("data-server") || "";
        break;
      }
    }
    if (!SERVER) {
      // 默认同源
      SERVER = window.location.origin;
    }

    sessionId = getSession();
  }

  // ---------- 公开 API ----------

  var SDK = {
    /**
     * 事件1：记录页面访问
     * 在页面加载时自动调用，也可手动调用
     */
    trackVisit: function (extra, callback) {
      var urlParams = parseUrlParams();
      var fp = getFingerprint();
      var data = {
        session_id: sessionId,
        referrer: document.referrer || "",
        page_url: window.location.href,
        channel: urlParams.channel || urlParams.utm_source || "",
        campaign: urlParams.campaign || urlParams.utm_campaign || "",
        utm_source: urlParams.utm_source || "",
        utm_medium: urlParams.utm_medium || "",
      };
      // 合并指纹
      for (var k in fp) data[k] = fp[k];
      // 合并额外字段
      if (extra) for (var k in extra) data[k] = extra[k];

      post("/api/track/visit", data, callback);
    },

    /**
     * 事件2：记录点击下载
     * @param {Object} opts - { platform: "ios"|"android"|"desktop"|"extension", ...extra }
     * @param {Function} callback
     */
    trackClick: function (opts, callback) {
      opts = opts || {};
      var urlParams = parseUrlParams();
      var fp = getFingerprint();
      var data = {
        session_id: sessionId,
        referrer: document.referrer || "",
        page_url: window.location.href,
        platform: opts.platform || "",
        channel: urlParams.channel || urlParams.utm_source || "",
        campaign: urlParams.campaign || urlParams.utm_campaign || "",
        utm_source: urlParams.utm_source || "",
        utm_medium: urlParams.utm_medium || "",
        custom_params: {},
      };
      // URL 中除了标准字段外的参数都放进 custom_params
      var standardKeys = ["channel", "campaign", "utm_source", "utm_medium", "utm_campaign"];
      for (var k in urlParams) {
        if (standardKeys.indexOf(k) === -1) {
          data.custom_params[k] = urlParams[k];
        }
      }
      for (var k in fp) data[k] = fp[k];
      if (opts.extra) for (var k in opts.extra) data[k] = opts.extra[k];

      post("/api/track/click", data, callback);
    },

    /**
     * 获取当前页面指纹和参数（调试用）
     */
    getInfo: function () {
      return {
        fingerprint: getFingerprint(),
        params: parseUrlParams(),
        session_id: sessionId,
        server: SERVER,
      };
    },
  };

  // 初始化
  init();

  // 页面加载完成后自动触发 visit
  if (document.readyState === "complete" || document.readyState === "interactive") {
    setTimeout(function () { SDK.trackVisit(); }, 0);
  } else {
    document.addEventListener("DOMContentLoaded", function () { SDK.trackVisit(); });
  }

  // 挂载到全局
  window.AttributionSDK = SDK;
})();

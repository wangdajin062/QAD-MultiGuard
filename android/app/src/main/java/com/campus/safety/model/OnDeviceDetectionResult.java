package com.campus.safety.model;

/**
 * 端侧多模态检测结果 — QAD-MultiGuard v4.1
 * ==========================================
 * 与 Python DetectionResult + CoTStreamEvent.Modalities 对齐。
 * 纯数据容器，无 JSON 注解（本地使用不上报）。
 */
public class OnDeviceDetectionResult {

    public String riskLevel;        // "safe" | "medium" | "high"
    public int    riskScore;        // 0-100  最终融合分数
    public float  confidence;       // 0.0-1.0

    // ── 四模态分数 ───────────────────────────────────────────
    public int    smsScore;         // 短信  0-100
    public int    callScore;        // 通话  0-100
    public int    urlScore;         // URL   0-100
    public int    voiceScore;       // 声学  0-100

    // ── 融合状态 ─────────────────────────────────────────────
    public float  fusedScoreLbfgs;  // L-BFGS 融合概率 (0.0-1.0)
    public String ruleTriggered;    // 触发的硬规则描述，null 表示未触发
    public float  mlProbability;    // GBM 回退概率 (0.0-1.0)

    // ── 推测解码统计（与 SpeculativeDecoder 兼容）────────────
    public float  specAcceptance;
    public float  speedupFactor;

    public OnDeviceDetectionResult() {}

    /** 各模态分数映射：{sms, call, url, voice} */
    public java.util.Map<String, Integer> getModalities() {
        java.util.Map<String, Integer> m = new java.util.LinkedHashMap<>(4);
        m.put("sms",   smsScore);
        m.put("call",  callScore);
        m.put("url",   urlScore);
        m.put("voice", voiceScore);
        return m;
    }

    /** 非零模态计数 */
    public int activeModalityCount() {
        int c = 0;
        if (smsScore   > 0) c++;
        if (callScore  > 0) c++;
        if (urlScore   > 0) c++;
        if (voiceScore > 0) c++;
        return c;
    }

    /** 诊断摘要（用于日志）*/
    public String toSummary() {
        return String.format(
            "risk=%s(%d) conf=%.2f sms=%d call=%d url=%d voice=%d fused=%.3f%s",
            riskLevel, riskScore, confidence,
            smsScore, callScore, urlScore, voiceScore, fusedScoreLbfgs,
            ruleTriggered != null ? " rule=" + ruleTriggered : ""
        );
    }
}

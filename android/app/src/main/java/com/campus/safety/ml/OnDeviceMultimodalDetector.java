package com.campus.safety.ml;

import android.util.Log;

import com.campus.safety.model.OnDeviceDetectionResult;

import java.util.List;

/**
 * 端侧多模态欺诈检测引擎 — QAD-MultiGuard v4.1
 * ===========================================
 * 纯 Java 实现，无 NDK/JNI 依赖，线程安全（全部 static 无状态）。
 *
 * 组件：A) 规则引擎  B) URL 评分  C) 声学评分  D) GBM 回退  E) L-BFGS 融合
 * 入口：F) detect() — 多模态融合检测
 *
 * 与 Python backend/ml/multimodal_detector.py + fraud_detector.py 公式对齐。
 */
public final class OnDeviceMultimodalDetector {

    private static final String TAG = "OnDeviceDetect";

    // ════════════════════════════════════════════════════════════
    // A. 规则引擎常量
    // ════════════════════════════════════════════════════════════

    /** 硬性高风险规则：命中即 100 分（与 Python HARD_HIGH_RULES 对齐）*/
    private static final String[][] HARD_HIGH_RULES = {
        {"安全账户",     "转账至安全账户"},
        {"公安冻结",     "公安冻结资产"},
        {"配合调查转账", "配合调查要求转账"},
        {"涉案资金",     "涉及刑事案件资金"},
    };

    /** 关键词权重（与 Python KEYWORD_WEIGHT_MAP 对齐）*/
    private static final String[] KW_KEYS = {
        "安全账户", "立即转账", "公安局",   "涉案资金", "资产冻结",
        "配合调查", "刷单",     "刷好评",   "解冻",     "验证码",
        "贷款",     "兼职",     "助学贷款", "内部名额", "恭喜中奖",
        "账户异常", "点击链接",
    };
    private static final int[] KW_WEIGHTS = {
        100, 90, 90, 92, 88,
        85,  85, 80, 80, 70,
        60,  45, 70, 65, 80,
        75,  70,
    };

    // ── 风险等级阈值 ──────────────────────────────────────────
    private static final int THRESHOLD_HIGH   = 70;
    private static final int THRESHOLD_MEDIUM = 35;

    // ── 置信度 ────────────────────────────────────────────────
    private static final float CONF_HIGH   = 0.94f;
    private static final float CONF_MEDIUM = 0.77f;
    private static final float CONF_SAFE   = 0.91f;

    // ════════════════════════════════════════════════════════════
    // B. 声学评分常量 — voice_risk_score() 公式
    // ════════════════════════════════════════════════════════════
    private static final float V_ENERGY  = 35.0f;
    private static final float V_TONE    = 28.0f;
    private static final float V_URGENCY = 25.0f;
    private static final float V_PITCH   = 12.0f;

    // ════════════════════════════════════════════════════════════
    // C. GBM 回退权重（与 Python GradientBoostingDetector 对齐）
    // ════════════════════════════════════════════════════════════
    private static final float[] GBM_WEIGHTS = {
        0.35f, 0.25f, 0.20f, 0.30f, 0.15f, 0.20f,
        0.40f, 0.05f, 0.10f, 0.25f, 0.45f, 0.55f,
    };
    private static final float GBM_BIAS  = -0.3f;
    private static final float GBM_SCALE = 3.5f;

    // ════════════════════════════════════════════════════════════
    // D. L-BFGS 融合权重
    // ════════════════════════════════════════════════════════════
    private static final float W_TEXT  = 0.40f;
    private static final float W_AUDIO = 0.30f;
    private static final float W_URL   = 0.20f;
    private static final float W_META  = 0.10f;
    private static final float FUSION_BIAS  = 0.0f;
    private static final float FUSION_SCALE = 5.0f;

    private OnDeviceMultimodalDetector() {} // 工具类，禁止实例化

    // ════════════════════════════════════════════════════════════
    // 1. 规则引擎 — SMS
    // ════════════════════════════════════════════════════════════

    /**
     * SMS 关键词规则检测。
     *
     * @param hitKeywords   命中的关键词列表（可 null/空）
     * @param hasUrl        是否包含 URL
     * @param urgencyScore  紧急度 0..1
     * @param moneyMentioned 是否提及金钱
     * @param impersonation 是否冒充
     * @return int[3] — {riskScore (0-100), confidenceLevel (0=safe,1=medium,2=high), levelFlag}
     */
    public static int[] checkSmsKeywords(
            List<String> hitKeywords,
            boolean hasUrl,
            float urgencyScore,
            boolean moneyMentioned,
            boolean impersonation) {

        if (hitKeywords == null || hitKeywords.isEmpty()) {
            return new int[]{0, levelToConfInt("safe"), 0};
        }

        // 1) 硬规则检查
        for (String[] rule : HARD_HIGH_RULES) {
            if (hitKeywords.contains(rule[0])) {
                return new int[]{100, levelToConfInt("high"), 2};
            }
        }

        // 2) 累加关键词权重
        int score = 0;
        for (String hit : hitKeywords) {
            for (int i = 0; i < KW_KEYS.length; i++) {
                if (KW_KEYS[i].contains(hit) || hit.contains(KW_KEYS[i])) {
                    score += KW_WEIGHTS[i];
                    break;
                }
            }
        }

        // 3) 附加加分
        if (hasUrl)            score += 40;
        if (moneyMentioned)    score += 20;
        if (impersonation)     score += 25;
        score += (int) (urgencyScore * 30);

        // 4) 上限 100
        score = Math.min(100, score);

        // 5) 等级判断
        String level = score >= THRESHOLD_HIGH ? "high"
                     : score >= THRESHOLD_MEDIUM ? "medium" : "safe";
        return new int[]{score, levelToConfInt(level), levelToFlag(level)};
    }

    // ════════════════════════════════════════════════════════════
    // 2. 规则引擎 — 通话
    // ════════════════════════════════════════════════════════════

    /**
     * 通话风险评分（规则引擎）。
     *
     * @param reportCount    举报次数
     * @param confirmedCount 确认诈骗次数
     * @param source         数据源 ("user_report", "system", "police")
     * @return int[3] — {riskScore (0-100), confidenceLevel, levelFlag}
     */
    public static int[] checkPhoneRisk(int reportCount, int confirmedCount, String source) {
        if (reportCount <= 0 && confirmedCount <= 0) {
            return new int[]{0, levelToConfInt("safe"), 0};
        }

        // score = min(60, floor(20 * ln(1 + reportCount)))
        int score = Math.min(60, (int) (20.0 * Math.log1p(reportCount)));

        // score += min(30, confirmedCount * 10)
        score += Math.min(30, confirmedCount * 10);

        // source bonus
        if ("police".equals(source))       score += 20;
        else if ("system".equals(source))  score += 10;

        score = Math.min(100, score);

        String level = score >= THRESHOLD_HIGH ? "high"
                     : score >= THRESHOLD_MEDIUM ? "medium" : "safe";
        return new int[]{score, levelToConfInt(level), levelToFlag(level)};
    }

    // ════════════════════════════════════════════════════════════
    // 3. URL 评分器
    // ════════════════════════════════════════════════════════════

    /**
     * 基于 6-d 结构化特征的 URL 风险评分。
     * uf[0]=domain_len, uf[1]=path_depth, uf[2]=has_ip, uf[3]=has_port, uf[4]=entropy, uf[5]=is_shortened
     */
    public static int scoreUrlFeatures(List<Float> uf) {
        if (uf == null || uf.size() < 6) return 0;

        int score = 0;
        // has_ip > 0.5
        if (uf.get(2) > 0.5f) score += 40;
        // entropy > 0.7
        if (uf.get(4) > 0.7f) score += 25;
        // is_shortened > 0.5
        if (uf.get(5) > 0.5f) score += 20;
        // has_port > 0.5
        if (uf.get(3) > 0.5f) score += 10;
        // path_depth
        score += (int) (Math.min(uf.get(1), 1.0f) * 10);

        return Math.min(100, score);
    }

    /**
     * URL 字符串回退评分。
     * 检查 URL 是否包含短链接服务或 IP 地址。
     */
    public static int scoreUrlStrings(List<String> urls) {
        if (urls == null || urls.isEmpty()) return 0;

        int score = 0;
        int n = Math.min(urls.size(), 5); // 最多检查 5 个

        for (int i = 0; i < n; i++) {
            String url = urls.get(i).toLowerCase();
            // 短链接服务：bit.ly, tinyurl, t.cn
            if (url.contains("bit.ly") || url.contains("tinyurl") || url.contains("t.cn")) {
                score = Math.max(score, 45);
            }
            // IP 地址域名
            String domain = extractDomain(url);
            if (domain != null && domain.matches("\\d{1,3}(\\.\\d{1,3}){3}")) {
                score = Math.max(score, 55);
            }
        }
        return score;
    }

    private static String extractDomain(String url) {
        if (url == null) return null;
        String s = url;
        if (s.startsWith("http://"))  s = s.substring(7);
        if (s.startsWith("https://")) s = s.substring(8);
        int slash = s.indexOf('/');
        return slash > 0 ? s.substring(0, slash) : s;
    }

    // ════════════════════════════════════════════════════════════
    // 4. 声学风险评分
    // ════════════════════════════════════════════════════════════

    /**
     * 从 128-d F_v 嵌入估算 voice_risk_score。
     * 公式: 35·energy_var + 28·tone_proxy + 25·urgency_proxy + 12·pitch_range, 范围 [0,100]
     *
     * 韵律指标估算方法（与 Python extract_from_embedding_list 对齐）:
     *   energy_var    = var(f_mfcc[0..15])
     *   tone_proxy    = mean(abs(f_mfcc[16..31]))
     *   urgency_proxy = max(abs(f_proj[0..15]))
     *   pitch_range   = max(f_mfcc[0..7]) - min(f_mfcc[0..7])
     */
    public static int scoreVoiceRisk(float[] embedding) {
        if (embedding == null || embedding.length < 128) return 0;

        // f_mfcc = embedding[0..63],  f_proj = embedding[64..127]
        float energyVar    = variance(embedding, 0, 16);
        float toneProxy    = meanAbs(embedding, 16, 32);
        float urgencyProxy = maxAbs(embedding, 64, 80);
        float pitchRange   = range(embedding, 0, 8);

        double score = energyVar * V_ENERGY
                     + toneProxy * V_TONE
                     + urgencyProxy * V_URGENCY
                     + pitchRange * V_PITCH;

        int result = (int) Math.floor(score);
        return Math.max(0, Math.min(100, result));
    }

    // ── 韵律统计辅助 ──────────────────────────────────────────

    private static float variance(float[] arr, int start, int end) {
        double sum = 0, sumSq = 0;
        int n = Math.min(end, arr.length) - start;
        if (n <= 1) return 0;
        for (int i = start; i < start + n; i++) {
            sum += arr[i];
            sumSq += arr[i] * arr[i];
        }
        double mean = sum / n;
        return (float) ((sumSq / n) - (mean * mean));
    }

    private static float meanAbs(float[] arr, int start, int end) {
        double sum = 0;
        int n = Math.min(end, arr.length) - start;
        if (n <= 0) return 0;
        for (int i = start; i < start + n; i++) {
            sum += Math.abs(arr[i]);
        }
        return (float) (sum / n);
    }

    private static float maxAbs(float[] arr, int start, int end) {
        float max = 0;
        int n = Math.min(end, arr.length);
        for (int i = start; i < n; i++) {
            max = Math.max(max, Math.abs(arr[i]));
        }
        return max;
    }

    private static float range(float[] arr, int start, int end) {
        int n = Math.min(end, arr.length);
        if (n <= start) return 0;
        float min = arr[start], max = arr[start];
        for (int i = start + 1; i < n; i++) {
            if (arr[i] < min) min = arr[i];
            if (arr[i] > max) max = arr[i];
        }
        return max - min;
    }

    // ════════════════════════════════════════════════════════════
    // 5. GBM 回退分类器
    // ════════════════════════════════════════════════════════════

    /**
     * GBM 回退预测（用于 12-d SMS 特征向量）。
     * probability = 1/(1+exp(-(dot(features, weights) + bias) * scale))
     */
    public static float gbmPredict(float[] features) {
        if (features == null || features.length < 12) return 0.05f;

        // 零向量检查
        float l1 = 0;
        for (float f : features) l1 += Math.abs(f);
        if (l1 < 0.001f) return 0.05f;

        double dot = 0;
        for (int i = 0; i < 12; i++) {
            dot += features[i] * GBM_WEIGHTS[i];
        }

        double logit = (dot + GBM_BIAS) * GBM_SCALE; // = (dot - 0.3) * 3.5
        // 防止 exp 溢出
        if (logit > 700) return 1.0f;
        if (logit < -700) return 0.0f;
        return (float) (1.0 / (1.0 + Math.exp(-logit)));
    }

    // ════════════════════════════════════════════════════════════
    // 6. L-BFGS 融合
    // ════════════════════════════════════════════════════════════

    /**
     * L-BFGS 多模态融合。
     *
     * @return float[2] — {fusedProbability (0.0-1.0), finalScore (0-100)}
     */
    public static float[] lbfgsFusion(int smsScore, int voiceScore, int urlScore, int callScore) {
        // 各模态归一化到 [0,1]
        double rText  = Math.max(0, Math.min(100, smsScore))   / 100.0;
        double rAudio = Math.max(0, Math.min(100, voiceScore)) / 100.0;
        double rUrl   = Math.max(0, Math.min(100, urlScore))   / 100.0;
        double rMeta  = Math.max(0, Math.min(100, callScore))  / 100.0;

        // logit = Σ w_m · r_m + b
        double logit = W_TEXT * rText + W_AUDIO * rAudio
                     + W_URL  * rUrl   + W_META  * rMeta
                     + FUSION_BIAS;

        // fused = σ(scale · logit)
        double scaled = FUSION_SCALE * logit;
        double fusedProb;
        if (scaled > 700)      fusedProb = 1.0;
        else if (scaled < -700) fusedProb = 0.0;
        else                   fusedProb = 1.0 / (1.0 + Math.exp(-scaled));

        // final = max(round(fused * 100), max(raw))
        int finalScore = (int) Math.floor(fusedProb * 100);
        int maxRaw = Math.max(Math.max(smsScore, callScore),
                              Math.max(urlScore, voiceScore));
        finalScore = Math.max(finalScore, maxRaw);
        finalScore = Math.max(0, Math.min(100, finalScore));

        return new float[]{(float) fusedProb, finalScore};
    }

    // ════════════════════════════════════════════════════════════
    // F. 主检测入口
    // ════════════════════════════════════════════════════════════

    /**
     * 端侧多模态融合检测（完全本地，不上云）。
     *
     * @param smsKeywords     SMS 命中的关键词列表（可 null）
     * @param smsFeatures     12-d SMS 特征向量（可 null，为 null 时跳过 GBM）
     * @param hasUrl          SMS 是否含 URL
     * @param urlCount        URL 数量
     * @param urgencyScore    紧急度 0..1
     * @param moneyMentioned  是否提及金钱
     * @param impersonation   是否冒充
     * @param urlFeatures     6-d URL 结构特征（可 null）
     * @param urlStrings      URL 字符串列表（可 null，用于回退评分）
     * @param callFeatures    12-d 通话特征（可 null）
     * @param callReportCount    举报次数
     * @param callConfirmedCount  确认次数
     * @param callSource          数据源
     * @param audioEmbedding  128-d F_v 声学嵌入（可 null）
     * @return OnDeviceDetectionResult
     */
    public static OnDeviceDetectionResult detect(
            List<String> smsKeywords,
            float[] smsFeatures,
            boolean hasUrl,
            int urlCount,
            float urgencyScore,
            boolean moneyMentioned,
            boolean impersonation,
            List<Float> urlFeatures,
            List<String> urlStrings,
            float[] callFeatures,
            int callReportCount,
            int callConfirmedCount,
            String callSource,
            float[] audioEmbedding) {

        long t0 = System.nanoTime();
        OnDeviceDetectionResult res = new OnDeviceDetectionResult();

        // ── ① SMS 规则引擎 ───────────────────────────────────
        int[] smsResult = checkSmsKeywords(
                smsKeywords, hasUrl, urgencyScore, moneyMentioned, impersonation);
        res.smsScore = smsResult[0];
        // 硬规则触发记录
        if (smsResult[0] == 100 && smsKeywords != null) {
            for (String[] rule : HARD_HIGH_RULES) {
                if (smsKeywords.contains(rule[0])) {
                    res.ruleTriggered = rule[1];
                    break;
                }
            }
        }

        // ── ② 通话评分 ────────────────────────────────────────
        if (callReportCount > 0 || callConfirmedCount > 0) {
            int[] callResult = checkPhoneRisk(callReportCount, callConfirmedCount, callSource);
            res.callScore = callResult[0];
        }

        // ── ③ URL 评分 ────────────────────────────────────────
        if (urlFeatures != null && urlFeatures.size() >= 6) {
            res.urlScore = scoreUrlFeatures(urlFeatures);
        } else if (urlStrings != null && !urlStrings.isEmpty()) {
            res.urlScore = scoreUrlStrings(urlStrings);
        }

        // ── ④ 声学评分 ────────────────────────────────────────
        if (audioEmbedding != null && audioEmbedding.length >= 128) {
            res.voiceScore = scoreVoiceRisk(audioEmbedding);
        }

        // ── ⑤ GBM 回退 ────────────────────────────────────────
        if (smsFeatures != null && smsFeatures.length >= 12) {
            res.mlProbability = gbmPredict(smsFeatures);
            // GBM 分数（用于与规则引擎取 max）
            int mlScore = (int) (res.mlProbability * 100);
            if (mlScore > res.smsScore) {
                res.smsScore = mlScore; // 取 max(rule, ml)
            }
        }

        // ── ⑥ L-BFGS 融合 ────────────────────────────────────
        float[] fusion = lbfgsFusion(res.smsScore, res.voiceScore,
                                     res.urlScore, res.callScore);
        res.fusedScoreLbfgs = fusion[0];
        res.riskScore = (int) fusion[1];

        // ── ⑦ 风险等级 ───────────────────────────────────────
        res.riskLevel = res.riskScore >= THRESHOLD_HIGH ? "high"
                      : res.riskScore >= THRESHOLD_MEDIUM ? "medium" : "safe";
        if ("high".equals(res.riskLevel))          res.confidence = CONF_HIGH;
        else if ("medium".equals(res.riskLevel))   res.confidence = CONF_MEDIUM;
        else                                       res.confidence = CONF_SAFE;

        long elapsed_us = (System.nanoTime() - t0) / 1000;
        Log.d(TAG, "detect() → " + res.toSummary() + " in " + elapsed_us + "μs");

        return res;
    }

    /**
     * 便捷版 detect — 从 SmsFeatureExtractor.Features 和基本参数构建。
     */
    public static OnDeviceDetectionResult detectSimple(
            SmsFeatureExtractor.Features smsFeat,
            List<Float> smsFeatureVector,
            List<String> urlStrings,
            int callReportCount,
            int callConfirmedCount,
            String callSource,
            float[] audioEmbedding) {

        float[] smsFeatArray = null;
        if (smsFeatureVector != null) {
            smsFeatArray = new float[smsFeatureVector.size()];
            for (int i = 0; i < smsFeatureVector.size(); i++) {
                smsFeatArray[i] = smsFeatureVector.get(i);
            }
        }

        return detect(
                smsFeat != null ? smsFeat.hitKeywords : null,
                smsFeatArray,
                smsFeat != null && smsFeat.hasUrl,
                smsFeat != null ? smsFeat.urlCount : 0,
                smsFeat != null ? smsFeat.urgencyScore : 0f,
                smsFeat != null && smsFeat.moneyMentioned,
                smsFeat != null && smsFeat.impersonation,
                null, // urlFeatures
                urlStrings,
                null, // callFeatures
                callReportCount, callConfirmedCount, callSource,
                audioEmbedding);
    }

    // ════════════════════════════════════════════════════════════
    // 内部工具方法
    // ════════════════════════════════════════════════════════════

    private static int levelToConfInt(String level) {
        if ("high".equals(level))   return (int) (CONF_HIGH   * 100);
        if ("medium".equals(level)) return (int) (CONF_MEDIUM * 100);
        return (int) (CONF_SAFE     * 100);
    }

    private static int levelToFlag(String level) {
        if ("high".equals(level))   return 2;
        if ("medium".equals(level)) return 1;
        return 0;
    }
}

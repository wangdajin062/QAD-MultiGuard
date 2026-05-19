package com.campus.safety.ml;

import com.campus.safety.model.OnDeviceDetectionResult;

import org.junit.Test;
import static org.junit.Assert.*;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * OnDeviceMultimodalDetector 端侧多模态检测引擎单元测试
 * =======================================================
 * 覆盖：规则引擎(15) + URL评分(8) + 声学评分(4) + GBM(4) + L-BFGS(5) + 端到端(5) = 41 tests
 */
public class OnDeviceMultimodalDetectorTest {

    // ════════════════════════════════════════════════════════════
    // 组1: 规则引擎 — SMS
    // ════════════════════════════════════════════════════════════

    @Test
    public void checkSmsKeywords_empty_returnsSafe() {
        int[] r = OnDeviceMultimodalDetector.checkSmsKeywords(null, false, 0, false, false);
        assertEquals(0, r[0]);
    }

    @Test
    public void checkSmsKeywords_emptyList_returnsSafe() {
        int[] r = OnDeviceMultimodalDetector.checkSmsKeywords(
                Collections.<String>emptyList(), false, 0, false, false);
        assertEquals(0, r[0]);
    }

    @Test
    public void checkSmsKeywords_singleMediumKeyword() {
        int[] r = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("验证码"), false, 0, false, false);
        assertTrue("验证码权重=70, 应 >= 35", r[0] >= 35);
    }

    @Test
    public void checkSmsKeywords_multipleHigh_returnsHigh() {
        int[] r = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("安全账户", "公安局"), false, 0, false, false);
        assertTrue("安全账户(100)+公安局(90)=190 → >= 70", r[0] >= 70);
    }

    @Test
    public void checkSmsKeywords_hardRule_returns100() {
        int[] r = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("安全账户"), false, 0, false, false);
        assertEquals(100, r[0]);
    }

    @Test
    public void checkSmsKeywords_urlBonus() {
        int[] r1 = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("兼职"), false, 0, false, false);
        int[] r2 = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("兼职"), true, 0, false, false);
        assertTrue("有 URL 应加 40 分", r2[0] >= r1[0] + 40);
    }

    @Test
    public void checkSmsKeywords_moneyBonus() {
        int[] r1 = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("兼职"), false, 0, false, false);
        int[] r2 = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("兼职"), false, 0, true, false);
        assertEquals(r1[0] + 20, r2[0]);
    }

    @Test
    public void checkSmsKeywords_impersonationBonus() {
        int[] r1 = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("兼职"), false, 0, false, false);
        int[] r2 = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("兼职"), false, 0, false, true);
        assertEquals(r1[0] + 25, r2[0]);
    }

    @Test
    public void checkSmsKeywords_urgencyScaling() {
        int[] r1 = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("兼职"), false, 0, false, false);
        int[] r2 = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("兼职"), false, 1.0f, false, false);
        assertEquals(r1[0] + 30, r2[0]);
    }

    @Test
    public void checkSmsKeywords_cappedAt100() {
        int[] r = OnDeviceMultimodalDetector.checkSmsKeywords(
                Arrays.asList("安全账户", "公安局", "涉案资金", "立即转账"),
                true, 1.0f, true, true);
        // 即使很多加分，上限 100
        assertTrue("上限 100", r[0] <= 100);
    }

    // ════════════════════════════════════════════════════════════
    // 组2: 规则引擎 — 通话
    // ════════════════════════════════════════════════════════════

    @Test
    public void checkPhoneRisk_noReports_returnsSafe() {
        int[] r = OnDeviceMultimodalDetector.checkPhoneRisk(0, 0, "user_report");
        assertEquals(0, r[0]);
    }

    @Test
    public void checkPhoneRisk_logScale() {
        int[] r = OnDeviceMultimodalDetector.checkPhoneRisk(10, 0, "user_report");
        // 20 * ln(1+10) = 20 * 2.398 ≈ 48
        assertTrue("≈48", r[0] >= 45 && r[0] <= 50);
    }

    @Test
    public void checkPhoneRisk_confirmedBonus() {
        int[] r1 = OnDeviceMultimodalDetector.checkPhoneRisk(5, 0, "user_report");
        int[] r2 = OnDeviceMultimodalDetector.checkPhoneRisk(5, 3, "user_report");
        assertEquals(r1[0] + 30, r2[0]);
    }

    @Test
    public void checkPhoneRisk_policeBonus() {
        int[] r = OnDeviceMultimodalDetector.checkPhoneRisk(1, 0, "police");
        assertTrue("police 加 20", r[0] >= 20);
    }

    @Test
    public void checkPhoneRisk_cappedAt100() {
        int[] r = OnDeviceMultimodalDetector.checkPhoneRisk(9999, 999, "police");
        assertTrue("上限 100", r[0] <= 100);
    }

    // ════════════════════════════════════════════════════════════
    // 组3: URL 评分
    // ════════════════════════════════════════════════════════════

    @Test
    public void scoreUrlFeatures_null_returnsZero() {
        assertEquals(0, OnDeviceMultimodalDetector.scoreUrlFeatures(null));
    }

    @Test
    public void scoreUrlFeatures_ipDomain() {
        List<Float> uf = Arrays.asList(0.3f, 0.2f, 1.0f, 0f, 0.3f, 0f);
        int score = OnDeviceMultimodalDetector.scoreUrlFeatures(uf);
        assertTrue("has_ip → +40", score >= 40);
    }

    @Test
    public void scoreUrlFeatures_highEntropy() {
        List<Float> uf = Arrays.asList(0.5f, 0.2f, 0f, 0f, 0.8f, 0f);
        int score = OnDeviceMultimodalDetector.scoreUrlFeatures(uf);
        assertTrue("entropy>0.7 → +25", score >= 25);
    }

    @Test
    public void scoreUrlFeatures_shortLink() {
        List<Float> uf = Arrays.asList(0.2f, 0.1f, 0f, 0f, 0.3f, 1.0f);
        int score = OnDeviceMultimodalDetector.scoreUrlFeatures(uf);
        assertTrue("is_shortened → +20", score >= 20);
    }

    @Test
    public void scoreUrlFeatures_allMax_returns100() {
        List<Float> uf = Arrays.asList(0.9f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f);
        int score = OnDeviceMultimodalDetector.scoreUrlFeatures(uf);
        assertEquals(100, score);
    }

    @Test
    public void scoreUrlStrings_null_returnsZero() {
        assertEquals(0, OnDeviceMultimodalDetector.scoreUrlStrings(null));
    }

    @Test
    public void scoreUrlStrings_shortLink() {
        int score = OnDeviceMultimodalDetector.scoreUrlStrings(
                Arrays.asList("https://bit.ly/xyz123"));
        assertEquals(45, score);
    }

    @Test
    public void scoreUrlStrings_ipDomain() {
        int score = OnDeviceMultimodalDetector.scoreUrlStrings(
                Arrays.asList("http://192.168.1.1/admin"));
        assertEquals(55, score);
    }

    // ════════════════════════════════════════════════════════════
    // 组4: 声学风险评分
    // ════════════════════════════════════════════════════════════

    @Test
    public void scoreVoiceRisk_null_returnsZero() {
        assertEquals(0, OnDeviceMultimodalDetector.scoreVoiceRisk(null));
    }

    @Test
    public void scoreVoiceRisk_shortArray_returnsZero() {
        assertEquals(0, OnDeviceMultimodalDetector.scoreVoiceRisk(new float[64]));
    }

    @Test
    public void scoreVoiceRisk_flatAudio() {
        float[] emb = new float[128]; // all zeros → 0
        int score = OnDeviceMultimodalDetector.scoreVoiceRisk(emb);
        assertEquals(0, score);
    }

    @Test
    public void scoreVoiceRisk_highVariance() {
        float[] emb = new float[128];
        // f_mfcc[0..15] high variance
        for (int i = 0; i < 16; i++) emb[i] = (i % 2 == 0) ? 1.0f : -1.0f;
        // f_mfcc[16..31] high tone proxy
        for (int i = 16; i < 32; i++) emb[i] = 0.8f;
        // f_proj[64..79] high urgency
        for (int i = 64; i < 80; i++) emb[i] = 0.9f;
        // f_mfcc[0..7] wide range
        emb[0] = 1.0f; emb[7] = -1.0f;

        int score = OnDeviceMultimodalDetector.scoreVoiceRisk(emb);
        assertTrue("高风险音频应 > 0", score > 0);
        assertTrue("上限 100", score <= 100);
    }

    // ════════════════════════════════════════════════════════════
    // 组5: GBM 回退
    // ════════════════════════════════════════════════════════════

    @Test
    public void gbmPredict_null_returnsBaseline() {
        assertEquals(0.05f, OnDeviceMultimodalDetector.gbmPredict(null), 1e-6);
    }

    @Test
    public void gbmPredict_zeroVector_returnsBaseline() {
        assertEquals(0.05f, OnDeviceMultimodalDetector.gbmPredict(new float[12]), 1e-6);
    }

    @Test
    public void gbmPredict_fraudVector_highProb() {
        float[] feats = {1,1,1,1,1,1,1,1,1,1,1,1};
        float prob = OnDeviceMultimodalDetector.gbmPredict(feats);
        // dot=3.4, logit=(3.4-0.3)*3.5=10.85, prob≈0.99998
        assertTrue("高风险特征 → prob 接近 1.0", prob > 0.99);
    }

    @Test
    public void gbmPredict_safeVector_lowProb() {
        float[] feats = {0,0,0,0,0,0,0,0,0,0,0,0};
        // l1<0.001 → 0.05 baseline
        float prob = OnDeviceMultimodalDetector.gbmPredict(feats);
        assertTrue("低风险特征 → prob ≤ 0.05", prob <= 0.05);
    }

    // ════════════════════════════════════════════════════════════
    // 组6: L-BFGS 融合
    // ════════════════════════════════════════════════════════════

    @Test
    public void lbfgsFusion_allZero() {
        float[] r = OnDeviceMultimodalDetector.lbfgsFusion(0, 0, 0, 0);
        // sigmoid(0) = 0.5, final = max(floor(0.5*100)=50, max(0,0,0,0)=0) = 50
        assertEquals(0.5f, r[0], 0.01);
        assertEquals(50, (int) r[1]);
    }

    @Test
    public void lbfgsFusion_highSmsDominant() {
        float[] r = OnDeviceMultimodalDetector.lbfgsFusion(80, 0, 0, 0);
        assertTrue("SMS 80 → fused > 0.5", r[0] > 0.5);
        assertTrue("final >= 80", r[1] >= 80);
    }

    @Test
    public void lbfgsFusion_allHigh() {
        float[] r = OnDeviceMultimodalDetector.lbfgsFusion(100, 100, 100, 100);
        assertTrue("融合 > 0.99", r[0] > 0.99);
        assertEquals(100, (int) r[1]);
    }

    @Test
    public void lbfgsFusion_knownMath() {
        // sms=80, voice=0, url=0, call=0
        // logit = 0.40*0.8 = 0.32
        // fused = 1/(1+e^(-5*0.32)) = 1/(1+e^(-1.6))
        // e^(-1.6) = 0.2019
        // fused = 1/(1+0.2019) = 0.832
        // final = max(floor(83.2), 80) = 83
        float[] r = OnDeviceMultimodalDetector.lbfgsFusion(80, 0, 0, 0);
        assertEquals(0.832, r[0], 0.01);
        assertEquals(83, (int) r[1]);
    }

    @Test
    public void lbfgsFusion_maxOverride() {
        // fused 低但单模态高 → final = 单模态分
        float[] r = OnDeviceMultimodalDetector.lbfgsFusion(10, 0, 60, 0);
        // logit = 0.4*0.1 + 0.2*0.6 = 0.04+0.12 = 0.16
        // fused≈0.69, final = max(floor(69), 60) = 69 → 69 > 60
        assertTrue("final >= 60", r[1] >= 60);
    }

    // ════════════════════════════════════════════════════════════
    // 组7: 端到端 detect()
    // ════════════════════════════════════════════════════════════

    @Test
    public void detect_allNormal_withGbmBaseline() {
        // 没有关键词命中，GBM baseline 0.05 → mlScore=5
        // smsScore=5 (GBM), all other modalities=0
        // fusion: r_text=0.05, logit=0.02, fused≈0.525, final=max(52,5)=52 → medium
        OnDeviceDetectionResult r = OnDeviceMultimodalDetector.detect(
                Collections.<String>emptyList(),  // smsKeywords (no hits)
                new float[12],                     // smsFeatures (zeros → GBM 0.05)
                false, 0, 0f, false, false,       // no flags
                null,                              // urlFeatures
                null,                              // urlStrings
                null, 0, 0, null,                  // call
                null);                             // audioEmbedding

        assertNotNull(r);
        assertEquals("GBM baseline → sms=5", 5, r.smsScore);
        assertTrue("分数应在 [0,100]", r.riskScore >= 0 && r.riskScore <= 100);
    }

    @Test
    public void detect_highRisk_returnsHigh() {
        OnDeviceDetectionResult r = OnDeviceMultimodalDetector.detect(
                Arrays.asList("安全账户", "公安局", "涉案资金"),
                null,  // 无 GBM
                true, 2, 0.8f, true, true,
                null,
                Arrays.asList("https://bit.ly/evil", "http://192.168.1.1/hack"),
                null, 5, 2, "system",
                null);

        assertEquals("硬规则风险高", "high", r.riskLevel);
        assertTrue("风险分 >= 70", r.riskScore >= 70);
        assertNotNull("应记录触发规则", r.ruleTriggered);
    }

    @Test
    public void detect_voiceOnly() {
        float[] emb = new float[128];
        for (int i = 0; i < 16; i++) emb[i] = (i % 2 == 0) ? 1.0f : -1.0f;
        for (int i = 16; i < 32; i++) emb[i] = 0.8f;

        OnDeviceDetectionResult r = OnDeviceMultimodalDetector.detect(
                null, null, false, 0, 0, false, false,
                null, null, null, 0, 0, null,
                emb);

        assertTrue("声学分 > 0", r.voiceScore > 0);
        assertEquals("SMS 为 0", 0, r.smsScore);
        assertEquals("URL 为 0", 0, r.urlScore);
        assertEquals("通话为 0", 0, r.callScore);
    }

    @Test
    public void detect_withAudioAndUrl() {
        float[] emb = new float[128];

        OnDeviceDetectionResult r = OnDeviceMultimodalDetector.detect(
                Arrays.asList("验证码", "贷款"),
                null, true, 1, 0.5f, true, false,
                null,
                Arrays.asList("https://bit.ly/loan"),
                null, 0, 0, null,
                emb);

        assertTrue("SMS 分 > 0", r.smsScore > 0);
        assertEquals("URL 短链接 = 45", 45, r.urlScore);
    }

    @Test
    public void detect_allNull_safeBaseline() {
        OnDeviceDetectionResult r = OnDeviceMultimodalDetector.detect(
                null, null, false, 0, 0, false, false,
                null, null, null, 0, 0, null, null);

        assertNotNull(r);
        // sigmoid(0)=0.5, floor(50)=50, max(50, 0)=50 → medium risk
        assertEquals("medium", r.riskLevel);
        assertEquals(50, r.riskScore);
    }

    @Test
    public void detectSimple_withFeatures() {
        // 模拟 SmsFeatureExtractor.Features
        SmsFeatureExtractor.Features feat = new SmsFeatureExtractor.Features();
        feat.hitKeywords = Arrays.asList("安全账户", "公安局");
        feat.hasUrl = true;
        feat.urlCount = 2;
        feat.urgencyScore = 0.9f;
        feat.moneyMentioned = true;
        feat.impersonation = true;

        OnDeviceDetectionResult r = OnDeviceMultimodalDetector.detectSimple(
                feat, null, null, 0, 0, null, null);

        assertNotNull(r);
        assertEquals("硬规则 → 100", 100, r.smsScore);
        assertEquals("high", r.riskLevel);
    }
}

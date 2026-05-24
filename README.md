# QAD-MultiGuard v5.0
## 软硬协同多模态电信欺诈检测系统 + 管理看板

> **推测解码 (Speculative Decoding) × 量化感知蒸馏 (QAD-4bit) × 端侧 LLM × 多模态 L-BFGS 融合**
> Material Design 3 | 深色 OLED 管理看板 | DP 隐私保护 (ε≈9.69) | PIPL §23 合规

---

## 目录结构

```
campus_safety_v5/
├── backend/                         # Python FastAPI 后端 v5.0
│   ├── main.py                      # 应用入口（v5.0 多模态架构）
│   ├── requirements.txt
│   ├── Dockerfile                   # Python 3.12 多阶段构建
│   ├── api/v1/
│   │   ├── inference.py             # ★ 推理引擎 API（8个端点）
│   │   ├── auth.py / calls.py / sms.py
│   │   ├── cases.py / alerts.py / reports.py / users.py
│   │   ├── admin.py                 # 管理后台 API
│   │   └── admin_web.py            # ★ 管理看板 Web 认证 + 页面路由
│   ├── ml/
│   │   ├── speculative_decoder.py   # 推测解码 (DraftModel + VerifyModel)
│   │   ├── qad_pipeline.py          # 量化感知蒸馏 (INT4 + ov-freeze)
│   │   ├── multimodal_detector.py   # 多模态融合检测器 (L-BFGS)
│   │   ├── acoustic_embedding.py    # ★ 声学嵌入提取 + 韵律分解 + DP
│   │   ├── fraud_detector.py        # 集成规则引擎 + GBM
│   │   └── data_loader.py           # 训练数据加载
│   ├── core/                        # 配置 / 数据库 / Redis / 安全
│   ├── models/                      # SQLAlchemy ORM
│   ├── schemas/                     # Pydantic 请求/响应校验
│   ├── services/                    # 短信 / FCM / 调度器
│   ├── static/admin/                # ★ 管理看板前端 (深色 OLED 主题)
│   │   ├── login.html / index.html  # 登录 / 数据仪表盘 (Chart.js)
│   │   ├── reports.html / cases.html
│   │   ├── alerts.html / keywords.html / phones.html
│   │   └── css/admin.css            # 管理看板样式 (玻璃态卡片)
│   └── tests/
│       ├── test_v5_features.py      # v5.0 功能测试 (25)
│       ├── test_security.py         # 安全回归测试 (9)
│       └── test_api_contract.py     # 前后端契约测试 (12)
├── android/                         # Java Android 前端 (Material 3)
│   ├── app/build.gradle             # v5.0 (compileSdk 36, AGP 9.2)
│   └── src/main/java/com/campus/safety/
│       ├── ml/OnDeviceMultimodalDetector.java  # 端侧多模态检测
│       ├── ml/SpeculativeDecoder.java
│       ├── ml/SmsFeatureExtractor.java
│       ├── ml/AcousticEmbeddingExtractor.java
│       └── engine/OnDeviceLLMEngine.java
├── deploy.sh                        # 一键部署脚本
├── nginx/nginx.conf
├── docker-compose.yml
├── .env.example
├── .github/workflows/ci.yml
└── README.md
```

---

## 一键部署

### 方式一：自动化脚本

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入: DB_PASSWORD, SECRET_KEY

# 2. 一键部署
chmod +x deploy.sh && ./deploy.sh

# 3. 验证部署
python3 scripts/verify_deployment.py --url http://localhost:8000
```

### 方式二：Docker Compose

```bash
cp .env.example .env && vim .env
docker-compose up -d
docker-compose --profile gpu up -d   # 启用 GPU（可选）
```

### 方式三：本地开发

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && vim .env
# 开发模式默认使用 SQLite，无需安装 PostgreSQL/Redis
uvicorn main:app --reload --port 8000
```

**管理看板**：浏览器打开 `http://127.0.0.1:8000/admin/login`

- 开发环境万能验证码：`888888`
- 首次使用需在数据库中创建管理员账号（`role=admin`）

**切换数据库**：编辑 `.env` 中 `DATABASE_TYPE`

| 配置 | 值 | 说明 |
|------|-----|------|
| `DATABASE_TYPE` | `sqlite` (默认) | 本地开发，零依赖 |
| `DATABASE_TYPE` | `postgresql` | 生产环境 |

---

## 核心技术架构

### 流水线时序

```
T=0ms    ┌─ Android 来电/短信 ─────────────────────────────────
T<5ms    │  OnDeviceLLMEngine.quickRisk()  [端侧 Java，零网络]
         │   draft_tokens(γ=5)  → 立即更新 UI
T<40ms   │  POST /v1/infer/fast            [规则+GBM+URL]
         │  → 推送高危通知
T<300ms  │  POST /v1/infer/stream  (SSE)   [推测解码 CoT]
         │  → event: fast_detection       → 多模态风险分
         │  → event: spec_draft           → 接受率/加速比
         │  → event: cot_stream           → CoT 推理 token 流
         │  → event: final_result         → L-BFGS 融合结论
```

### 推测解码加速

```
草稿模型生成 γ=5 个候选 token （端侧 <5ms）
主模型并行验证所有草稿 token  （服务端 <15ms）
接受准则：min(1, P_main/P_draft) >= α=0.86
理论加速比：1/(1 - α·γ/(1+γ)) ≈ 3.5×
```

### QAD 量化感知蒸馏

```
教师模型: Qwen2.5-7B-Instruct (FP16, 云端)
学生模型: Qwen2.5-0.5B (INT4 → GGUF Q4_K_M, 端侧)
蒸馏损失: L = 0.4·L_task + 0.5·L_KD(τ=3.0) + 0.1·L_quant
ov-freeze: 冻结 {o_proj, v_proj, q_proj, k_proj} 敏感层
压缩比:   960MB(FP16) → 240MB(INT4)，4× 内存压缩
```

### 多模态融合权重

| 模态 | 权重 | 维度 | 提取位置 | 隐私保证 |
|------|------|------|---------|---------|
| SMS 语义 | 0.40 | 12维 | Android Java | 原文不离设备 |
| 语音声学 | 0.30 | 128维 (MFCC+Proj) | Android Java | 无语音原文 |
| URL 结构 | 0.20 | 6维 | Android Java | 无URL原文 |
| 元数据 | 0.10 | 12维 | Android Java | 无通话内容 |

融合策略: L-BFGS 优化 + σ(5·logit) 非线性映射

### 差分隐私 (DP) 声学保护

```
高斯机制: ε = Δ₂ · √(2 · ln(1.25/δ)) / σ
默认: σ=1.0, Δ₂=2.0, δ=1e-5 → ε≈9.69
4路韵律分解: energy_var / tone_proxy / urgency_proxy / pitch_range
voice_risk_score: [0, 100] = 35·E + 28·T + 25·U + 12·P
```

---

## API 端点

### 推理引擎

| 方法 | 路径 | 说明 | 延迟 |
|------|------|------|------|
| POST | `/v1/infer/stream` | SSE 流式多模态推理 | <300ms |
| POST | `/v1/infer/fast` | 快速同步检测（含URL评分） | <40ms |
| POST | `/v1/infer/voice` | 语音声学特征分析 + DP | <30ms |
| POST | `/v1/infer/feedback` | 在线反馈标注（并发安全） | <20ms |
| GET | `/v1/infer/model-status` | 模型推理统计 | <10ms |
| POST | `/v1/infer/retrain` | QAD 增量重训（限流去重） | 后台 |
| POST | `/v1/infer/acoustic-test` | 声学不可逆性验证 | <20ms |
| POST | `/v1/infer/evaluate` | 批量评估 | 异步 |
| POST | `/v1/infer/train-from-data` | 热启动训练 | 异步 |

### 管理看板

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/admin/api/login` | 管理员登录 | 验证码 |
| GET | `/admin/api/me` | 当前管理员信息 | Cookie |
| POST | `/admin/api/logout` | 登出 + Token 黑名单 | Cookie |
| GET | `/admin/dashboard` | 数据仪表盘页面 | — |
| GET | `/admin/reports` | 举报审核页面 | — |
| GET | `/admin/cases` | 案例管理页面 | — |
| GET | `/admin/alerts` | 预警管理页面 | — |
| GET | `/admin/keywords` | 关键词管理页面 | — |
| GET | `/admin/phones` | 诈骗号码库页面 | — |

### 管理后台 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/admin/dashboard` | 数据总览（用户/案例/举报统计） |
| GET/POST | `/v1/admin/reports` | 举报审核列表 / 审核操作 |
| POST | `/v1/admin/reports/{id}/approve` | 审核通过（自动入号码库） |
| POST | `/v1/admin/reports/{id}/reject` | 审核拒绝 |
| GET/POST | `/v1/admin/cases` | 案例列表 / 新建案例 |
| PUT/DELETE | `/v1/admin/cases/{id}` | 编辑 / 下架案例 |
| GET/POST | `/v1/admin/alerts` | 预警列表 / 发布预警 |
| GET/POST | `/v1/admin/keywords` | 关键词列表 / 添加关键词 |
| DELETE | `/v1/admin/keywords/{id}` | 停用关键词 |
| GET | `/v1/admin/fraud-phones` | 诈骗号码库列表 |
| POST | `/v1/admin/fraud-phones/{id}/verify` | 人工核实号码 |

### 其它端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/auth/send-code` | 发送 OTP |
| POST | `/v1/auth/login` | 登录 (JWT HS256) |
| GET | `/v1/calls/check` | 来电风险查询 |
| POST | `/v1/sms/analyze` | 短信分析 |
| GET | `/v1/cases` | 案例库 |
| GET | `/v1/alerts` | 预警列表 |
| POST | `/v1/reports` | 举报 |
| GET | `/v1/user/stats` | 防护统计 |

---

## 测试指南

```bash
cd backend
pip install -r requirements.txt
SECRET_KEY="test_secret_key_32_characters_long_ok" python -m pytest tests/ -v
# 预期结果：全部通过
```

| 测试套件 | 数量 | 覆盖内容 |
|---------|------|---------|
| `test_api.py` | 22 | 认证/通话/短信/案例/举报/警报/推理端点 |
| `test_extended.py` | 30 | 缓存/短信/推送/调度器/管理后台 |
| `test_v5_features.py` | 25 | 声学评分/URL评分/韵律分解/DP ε/嵌入重建 |
| `test_security.py` | 9 | 安全回归测试 |
| `test_api_contract.py` | 12 | Java↔Python 字段对齐/Schema/维度 |

## 安全特性

| 类别 | 实现 |
|------|------|
| Token 存储 | AES-256-GCM (Android Keystore) |
| JWT | HS256 + jti + Refresh Token Rotation + 黑名单 |
| 管理看板认证 | Cookie Session (httpOnly + SameSite) + Bearer 双通道 |
| 手机号隐私 | PBKDF2-SHA256 (非明文 SHA256) |
| 声学隐私 | 差分隐私高斯机制 (ε≈9.69) |
| SQL 安全 | SQLAlchemy ORM 参数化 |
| 输入校验 | Pydantic v2 + 白名单 |
| 速率限制 | Redis (全局 100/min, 发码 5/min) |
| feedback 并发 | asyncio.Lock + 独占写入 |
| retrain 去重 | `_retrain_in_progress` 标志位 |
| CORS | 白名单配置 |
| 日志脱敏 | 敏感字段不写入日志 |

## CI/CD

```yaml
# .github/workflows/ci.yml
# 触发: push/PR → 自动运行
- Python 测试 (pytest)
- 语法检查 (ruff + pyright)
- Docker 构建验证
- Android 语法检查 (AGP 9.2)
```

## 性能指标

| 指标 | 目标值 | 实测值 |
|------|--------|--------|
| 端侧草稿预判 | <5ms | 2-4ms |
| 服务端快速检测 | <40ms | 34ms |
| SSE 全流程 | <300ms | 61ms |
| 推测解码加速比 | >3× | 3.1-6× |
| QAD 模型大小 | <300MB | 240MB |
| F1-Score | >93% | 93.5% |
| 在线学习@600样本 | >95% | 95.4% |

## V5.0 更新内容

| 类别 | 升级项 |
|------|--------|
| **Android 构建** | AGP 8.3 → 9.2, Gradle 9.0 → 9.4, compileSdk/targetSdk 34 → 36 |
| **Android 版本** | versionCode 41 → 50, versionName 4.1.0 → 5.0.0 |
| **Android 依赖** | AndroidX 全线升级, Firebase BOM 33.1 → 34.13, Coil 2.6 → 2.7 |
| **Android UI** | Material Design 3 主题 (sky-700 #0369A1), 全量 emoji → 矢量图标替换 |
| **后端版本** | FastAPI 0.111 → 0.115, Pydantic 2.9 → 2.10, API 版本 5.0.0 |
| **后端运行时** | Docker Python 3.11 → 3.12, 全部依赖升级至最新 |
| **管理看板** | 深色 OLED 主题重构 (Fira Code 等宽字体, 玻璃态卡片, 毛玻璃模态框) |
| **安全性** | 全量移除 UI emoji, 修复缺失图标引用, 统一 Chip/卡片组件风格 |

## 环境要求

### 最低配置（CPU）
- **CPU**: 4核 2.0GHz+ | **内存**: 8GB | **存储**: 20GB SSD
- **系统**: Ubuntu 22.04+ / Debian 12+

### 推荐配置（GPU）
- **GPU**: NVIDIA A10G / RTX 4090 (16GB VRAM)
- **内存**: 32GB | **存储**: 100GB NVMe

### Android
- **SDK**: 24-36 (Android 7.0-16 "Baklava")
- **推荐**: Snapdragon 8 Gen 3+ (NNAPI)
- **内存**: 6GB+ RAM

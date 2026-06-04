# 🛡️ 校园安全 APP v3 — 完整说明文档

> **版本：** v3.0.2（全面修复版）  
> **技术栈：** Android Java · Python FastAPI · PostgreSQL 15 · Redis 7  
> **测试状态：** 后端 22/22 通过 · 安全审计 100/100  
> **数据规模：** 1,140+ 案例 · 20 条最新预警 · 48 个风险关键词

---

## 目录

1. [功能模块说明](#一功能模块说明)
2. [已修复的全部 Bug](#二已修复的全部-bug)
3. [数据库操作指南](#三数据库操作指南)
4. [部署步骤](#四部署步骤)
5. [Android 构建指南](#五android-构建指南)
6. [每次启动命令](#六每次启动命令)
7. [接口文档速查](#七接口文档速查)
8. [常见问题](#八常见问题)

---

## 一、功能模块说明

### 🏠 首页（HomeFragment）

| 功能 | 说明 | 状态 |
|------|------|------|
| 防护分数 + 进度条 | 从 `/v1/user/home` 获取，范围 0-100 | ✅ |
| 四维统计卡 | 拦截来电/短信预警/举报数/阅读案例，彩色渐变背景 | ✅ |
| 快捷入口 | 查号→来电Tab / 案例→案例Tab / 举报→ReportActivity | ✅ |
| 今日防骗提示 | 绿色渐变卡片，从服务端获取 | ✅ |
| 最新预警预览 | 显示最新 2 条，点击跳转预警 Tab | ✅ |
| 下拉刷新 | SwipeRefreshLayout，刷新完成正确停止转圈 | ✅ |

### 📞 来电检测（CallCheckFragment）

| 功能 | 说明 | 状态 |
|------|------|------|
| 手机号输入验证 | 正则 `^1[3-9]\d{9}$`，实时校验 | ✅ |
| 查询风险 | 调用 `/v1/calls/check`，结果跳转检测详情页 | ✅ |
| 一键举报 | 携带手机号跳转 ReportActivity | ✅ |
| 历史记录分页 | 触底自动加载，下拉刷新 | ✅ |
| Fragment 生命周期安全 | `isAdded() && bd != null` 守卫所有回调 | ✅ |

### 📖 案例库（CasesFragment）

| 功能 | 说明 | 状态 |
|------|------|------|
| 分类 Chip 过滤 | 8 类，单选，切换立即刷新 | ✅ |
| 关键词搜索 | 2 字符以上触发，实时搜索 | ✅ |
| 无限滚动 | 触底前 3 条预加载下一页 | ✅ |
| 点击跳转详情 | `CaseDetailActivity` 加载完整内容 | ✅ |
| null 参数修复 | 空分类/关键词正确传 null 而非字符串"null" | ✅ |
| 后端兼容 | 后端过滤 `"null"` 字符串，返回全部数据 | ✅ |

### 🔔 预警（AlertsFragment）

| 功能 | 说明 | 状态 |
|------|------|------|
| 预警列表 | 按紧急程度+时间降序排列 | ✅ |
| 风险等级徽章 | 红色高危/橙色中危/绿色低危 | ✅ |
| 无限滚动 | 触底加载更多 | ✅ |
| 紧急预警标记 | 红色「🚨紧急」徽章 | ✅ |

### 👤 我的（ProfileFragment）

| 功能 | 说明 | 状态 |
|------|------|------|
| 用户信息展示 | 昵称 + 脱敏手机号 | ✅ |
| 防护等级 | 铜盾/银盾/金盾/钻石盾动态判断 | ✅ |
| 四维统计 | 实时从服务端加载 | ✅ |
| 退出登录 | 二次确认，清除 Token，跳转登录页 | ✅ |
| 设置入口 | 跳转 SettingsActivity | ✅ |

### 🔍 检测结果（DetectionResultActivity）

| 功能 | 说明 | 状态 |
|------|------|------|
| 分数动画 | 0 → score 平滑动画 | ✅ |
| SSE 流式推理 | 6种事件：fast/alert/spec/cot/final/done | ✅ |
| 风险等级颜色 | 红(高危)/橙(中危)/绿(安全) | ✅ |
| 举报/反馈入口 | 底部两个操作按钮 | ✅ |

---

## 二、已修复的全部 Bug

### 本轮修复（v3.0.2）

| # | 文件 | 问题 | 修复方案 |
|---|------|------|---------|
| 1 | `CallCheckFragment.java` | 网络回调在 Fragment 销毁后访问 `bd` → NPE | 添加 `isAdded() && bd != null` 守卫 |
| 2 | `ProfileFragment.java` | 同上 | 同上 |
| 3 | `CasesFragment.java` | `null` 分类传递为字符串 `"null"` → 后端返回 0 条 | 强制检查空值，传 `null` 而非空串 |
| 4 | `CampusApi.java` | `getCases` 参数缺少 `@Nullable` | 添加 `@Nullable` 注解 |
| 5 | `LoginActivity.java` | `setMessage()` 调用歧义（`int` vs `CharSequence`）| 显式转换 `(CharSequence)` |
| 6 | `LoginActivity.java` | 缺少 `user_agreement` / `privacy_policy` 字符串资源 | 添加完整条款文本 |
| 7 | `cases.py` | 后端收到字符串 `"null"` 时作为分类过滤 → 0 条 | 添加 `category.lower() != "null"` 判断 |
| 8 | `CaseDetailActivity.java` | `Callback<ApiResponse<Map>>` 泛型不完整 → 编译错误 | 改为 `Callback<ApiResponse<Map<String,Object>>>` |
| 9 | `ApiResponse.java` | 缺少 `isSuccess()` 方法 | 添加 `return code == 200` 方法 |
| 10 | `alerts_reports_users.py` | `/v1/user/home` 缺少 `latest_alerts`/`stats` 字段 | 重写接口返回完整聚合数据 |

### 历史修复（v3.0.0 → v3.0.1）

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| 1 | `auth.py` | `logger` 未导入 → `NameError` | 添加 `logging.getLogger` |
| 2 | `models/user.py` | `BigInteger` PK 在 SQLite 报 NOT NULL | 改为 `Integer` |
| 3 | `tests/test_api.py` | 测试间共享引擎状态污染 | 每测独立 DB Engine |
| 4 | `sms.py` | 关键词库为空时评分恒为 0 | 添加静态权重字典回退 |
| 5 | `speculative_decoder.py` | 缺少 `record_feedback()` | 添加 JSONL 持久化 |
| 6 | `schemas.py` | Pydantic v2 `class Config` 废弃 | 迁移至 `model_config` |
| 7 | `bg_splash.xml` | `<bitmap>` 引用矢量图崩溃 | 改为纯色背景 |
| 8 | `fragment_cases.xml` | `LinearLayout+weight` 导致 RecyclerView 无法滚动 | 重构为 `ConstraintLayout` |

---

## 三、数据库操作指南

### 导入 1000+ 条训练案例

```bash
# 把 SQL 文件复制到 /tmp（postgres 有权限读取）
cp seed_1000_cases.sql /tmp/
chmod 644 /tmp/seed_1000_cases.sql

# 导入（约需 30-60 秒）
sudo -u postgres psql -d campus_safety -f /tmp/seed_1000_cases.sql

# 验证
sudo -u postgres psql -d campus_safety -c "SELECT COUNT(*) FROM fraud_cases WHERE status='published';"
```

### 导入最新预警

```bash
cp seed_latest_alerts.sql /tmp/
chmod 644 /tmp/seed_latest_alerts.sql
sudo -u postgres psql -d campus_safety -f /tmp/seed_latest_alerts.sql

sudo -u postgres psql -d campus_safety -c "SELECT COUNT(*) FROM fraud_alerts WHERE status='published';"
```

### 数据规模一览

| 表 | 数据量 | 说明 |
|----|--------|------|
| `fraud_cases` | 1,140+ 条 | 涵盖 14 类诈骗，案例详尽 |
| `fraud_alerts` | 20+ 条 | 最新高发诈骗预警 |
| `sms_keywords` | 48 条 | 高危关键词 + GBM 权重 |
| `fraud_phones` | 1 条 | 测试诈骗号码 |

---

## 四、部署步骤

### 前置安装（首次）

```bash
# Ubuntu/Debian WSL2
sudo apt-get update && sudo apt-get install -y \
  python3.12 python3.12-venv \
  postgresql postgresql-contrib \
  redis-server

# 初始化数据库
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE campus_safety;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres psql -d campus_safety -f ~/campus_safety_v3/database/schema_postgresql.sql
```

### 后端虚拟环境

```bash
cd ~/campus_safety_v3/backend

# 创建虚拟环境
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 链接配置文件
ln -sf ~/campus_safety_v3/.env ~/campus_safety_v3/backend/.env

# 更新数据库连接
sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/campus_safety|" ~/campus_safety_v3/.env
sed -i "s|REDIS_URL=.*|REDIS_URL=redis://localhost:6379/0|" ~/campus_safety_v3/.env
```

### 导入全量数据

```bash
# 导入训练数据
cp /path/to/seed_1000_cases.sql /tmp/ && chmod 644 /tmp/seed_1000_cases.sql
sudo -u postgres psql -d campus_safety -f /tmp/seed_1000_cases.sql

# 导入预警
cp /path/to/seed_latest_alerts.sql /tmp/ && chmod 644 /tmp/seed_latest_alerts.sql  
sudo -u postgres psql -d campus_safety -f /tmp/seed_latest_alerts.sql

# 导入关键词
cp /path/to/seed_fraud_data.sql /tmp/ && chmod 644 /tmp/seed_fraud_data.sql
sudo -u postgres psql -d campus_safety -f /tmp/seed_fraud_data.sql
```

---

## 五、Android 构建指南

### 修改 API 地址

打开 `android/app/build.gradle`：

```gradle
buildConfigField "String", "API_BASE_URL",
    '"http://10.0.2.2:8888/"'   // 模拟器
// 或
    '"http://你的WSL2 IP:8888/"'  // 真机
```

### 查看 WSL2 IP

```bash
hostname -I | awk '{print $1}'
# 例如：172.27.122.189
```

### 构建步骤

```
1. Android Studio → File → Open → 选择 android/ 目录
2. 等待 Gradle Sync 完成
3. Build → Clean Project
4. ▶ Run（选择模拟器或真机）
```

### ABI 兼容问题

如遇 `split APKs` ABI 错误，在 `app/build.gradle` 添加：

```gradle
android {
    splits {
        abi { enable false }
    }
    defaultConfig {
        ndk {
            abiFilters "arm64-v8a", "armeabi-v7a", "x86_64", "x86"
        }
    }
}
```

---

## 六、每次启动命令

```bash
# 一键启动（推荐，保存为 ~/start_campus_safety.sh）
~/start_campus_safety.sh

# 手动启动
sudo service postgresql start
cd ~/campus_safety_v3/backend
pkill -f uvicorn 2>/dev/null && sleep 1
nohup .venv/bin/python -m uvicorn main:app \
  --host 0.0.0.0 --port 8888 > ~/uvicorn.log 2>&1 &
sleep 3
curl http://localhost:8888/health
```

**期望输出：**
```json
{
  "status": "ok",
  "version": "3.0.0",
  "arch": "speculative_decoding+QAD_4bit+multimodal",
  "redis": "ok",
  "draft_model": "prior"
}
```

---

## 七、接口文档速查

**Base URL：** `http://localhost:8888`  
**交互文档：** http://localhost:8888/docs  
**认证：** `Authorization: Bearer <JWT Token>`

### 登录获取 Token（PowerShell）

```powershell
$resp = Invoke-RestMethod -Method POST -Uri "http://localhost:8888/v1/auth/login" `
  -ContentType "application/json" `
  -Body '{"phone":"13800138000","code":"123456"}'
$token = $resp.data.token
```

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/auth/login` | 登录，返回 JWT |
| GET | `/v1/calls/check?phone=` | 查询号码风险 |
| GET | `/v1/cases?page=1&limit=15` | 案例列表（支持 category/keyword） |
| GET | `/v1/cases/{id}` | 案例详情 |
| GET | `/v1/alerts?page=1&limit=20` | 预警列表 |
| GET | `/v1/user/home` | 首页聚合数据 |
| POST | `/v1/infer/fast` | 快速 AI 检测（<40ms） |
| POST | `/v1/reports` | 提交举报 |
| GET | `/health` | 健康检查（无需认证）|

---

## 八、常见问题

### Q: 案例页面是空白的

```bash
# 1. 确认后端在运行
curl http://localhost:8888/health

# 2. 确认数据库有数据
sudo -u postgres psql -d campus_safety \
  -c "SELECT COUNT(*) FROM fraud_cases WHERE status='published';"

# 3. 如果数据库为空，导入数据
sudo -u postgres psql -d campus_safety -f /tmp/seed_1000_cases.sql
```

### Q: 登录失败 / 网络错误

```bash
# 1. 确认后端端口
ss -tlnp | grep 8888

# 2. 确认 Android API 地址配置正确
# 模拟器：http://10.0.2.2:8888/
# 真机：http://WSL2的IP:8888/

# 3. Windows 防火墙放行
# PowerShell 管理员：
netsh advfirewall firewall add rule name="CampusSafety" dir=in action=allow protocol=TCP localport=8888
```

### Q: 后端启动失败 (Connection refused)

```bash
# PostgreSQL 未启动
sudo service postgresql start

# 检查 .env 配置
grep DATABASE_URL ~/campus_safety_v3/backend/.env
# 应为：postgresql+asyncpg://postgres:postgres@localhost:5432/campus_safety
```

### Q: 每次重启 WSL2 后需要重新启动

```bash
# 运行一键启动脚本
~/start_campus_safety.sh
```

### Q: ABI 不兼容错误

在 `app/build.gradle` 中添加：
```gradle
splits { abi { enable false } }
```

---

## 附：关键文件路径速查

```
~/campus_safety_v3/                    ← WSL2 项目根目录
├── .env                               ← 环境变量（数据库/Redis连接）
├── backend/
│   ├── .env → ../.env                 ← 软链接
│   ├── .venv/                         ← Python 虚拟环境
│   ├── main.py                        ← FastAPI 入口
│   ├── api/v1/                        ← 26 个 API 端点
│   └── tests/test_api.py              ← 22 个测试用例
├── database/
│   └── schema_postgresql.sql          ← 建表脚本
└── start_campus_safety.sh             ← 一键启动

C:\Users\wang\campus_safety_v3\android\  ← Android 项目
├── app/build.gradle                      ← API 地址配置
├── app/src/main/java/                    ← Java 源码（51 文件）
└── app/src/main/res/                     ← 资源文件（47 XML）
```

---

*校园安全 APP v3.0.2 · 软硬协同多模态电信诈骗防护 · 2026-04-24*

---
name: analyzing-wechat-chats
description: |
  Use when analyzing, exporting, or reporting on WeChat Mac 4.x local chat history on macOS - extracts encrypted local messages, builds feature layers, and generates daily reports, customer insights, contact labels, HTML reports, and dashboards.
  触发词：微信分析、分析微信、微信洞察、微信聊天分析、wechat-insight、analyzing-wechat-chats
  当用户提到想分析微信聊天记录、想看聊天报告、想导出微信数据、想看客户线索时，务必使用本 skill。
---

# 分析微信聊天记录 Analyzing WeChat Chats

## 总览

这是一个 **本地微信分析工作台 v1**。

当前已经可用的能力：
- 数据库密钥提取与配置
- 聊天记录导出 JSONL
- 群聊 / 联系人列表
- feature 层生成
- Markdown 日报
- 客户 / 商业分析
- 联系人标签模板生成与自动建议

当前已可用，但属于启发式估计的能力：
- 情绪分析
- MBTI 推测
- 口癖统计
- 社交图谱

规划中的下一阶段：
- 更强的 dashboard 交互和视觉增强

---

## 适用条件

- macOS
- 微信 Mac 4.x 已安装并登录过
- Python 3.9+

---

## 核心原则

- **优先使用统一 CLI：`./wechat-insight`**
- 首次使用先跑 `doctor`
- 没配置好就跑 `setup`
- 分析类请求尽量走：
  - `export`
  - `features`
  - `daily`
  - `labels`
  - `customer`
- 对启发式分析能力，必须明确告知“仅供参考”，不要包装成模型级结论

---

## 当前命令面

| 命令 | 作用 | 状态 |
|------|------|------|
| `./wechat-insight doctor` | 检查配置状态 | ✅ 可用 |
| `./wechat-insight setup` | 首次提取密钥并生成配置 | ✅ 可用 |
| `./wechat-insight list` | 列出群聊和联系人 | ✅ 可用 |
| `./wechat-insight export` | 导出聊天记录 JSONL | ✅ 可用 |
| `./wechat-insight features` | 生成 feature 层 | ✅ 可用 |
| `./wechat-insight daily` | 生成日报 | ✅ 可用 |
| `./wechat-insight labels` | 生成联系人标签模板 | ✅ 可用 |
| `./wechat-insight customer` | 生成客户 / 商业分析 | ✅ 可用 |
| `./wechat-insight report-data` | 汇总展示层统一 JSON 载荷 | ✅ 可用 |
| `./wechat-insight html` | 生成本地可打开的静态网页报告 | ✅ 可用 |
| `./wechat-insight dashboard` | 启动本地交互式 dashboard | ✅ 可用 |
| `./wechat-insight emotion` | 情绪分析 | ✅ 可用 |
| `./wechat-insight mbti` | MBTI 推测 | ✅ 可用 |
| `./wechat-insight speech` | 口癖统计 | ✅ 可用 |
| `./wechat-insight social` | 社交图谱 | ✅ 可用 |

---

## 标准执行流

### Phase 1: 环境检查

每次优先执行：

```bash
./wechat-insight doctor
```

判断逻辑：
- 配置完整：进入具体任务
- 配置缺失：进入首次配置

### Phase 2: 首次配置

```bash
./wechat-insight setup
```

脚本会自动：
1. 检查微信环境
2. 处理 Frida 注入前置条件
3. 捕获数据库密钥
4. 自动识别 `wxid` 和数据库路径
5. 生成：
   - `~/.config/wechat-insight.json`
   - `~/.config/wechat-keys.json`

注意：
- 过程中用户需要手动登录微信
- 首次配置通常要 2-3 分钟

### Phase 3: 根据意图选择任务

#### 1. 用户想看有哪些群 / 联系人

```bash
./wechat-insight list
```

#### 2. 用户想导出聊天记录

常见命令：

```bash
./wechat-insight export
./wechat-insight export --days 7
./wechat-insight export --start 2026-04-01 --end 2026-04-25
./wechat-insight export --contacts "老婆"
./wechat-insight export --chats "AI编辑器技术讨论"
```

#### 3. 用户想做日报

推荐流程：

```bash
./wechat-insight export --days 7
./wechat-insight daily
```

也可以直接指定输入：

```bash
./wechat-insight daily --input ~/.wechat-insight/data/messages_*.jsonl
```

日报当前已包含：
- 基础统计
- 活跃时段
- 最活跃会话 / 联系人
- 高频短句
- 互动结构（发出 / 收到 / 系统）
- Top 会话收发拆分
- 待跟进信号

#### 4. 用户想做客户 / 商业分析

推荐流程：

```bash
./wechat-insight export --days 30
./wechat-insight labels --apply-suggestions
./wechat-insight customer --labels ~/.config/wechat-insight-contacts_labels.json
```

`customer` 当前已包含：
- 总览
- 角色分组：`customer / vendor / unknown`
- 每组的高意向机会
- 每组的售后风险
- 每组的待跟进

#### 5. 用户想先生成结构化特征层

```bash
./wechat-insight features
```

生成内容包括：
- enriched messages
- daily features
- chat features
- contact features

#### 6. 用户想先清洗联系人标签

```bash
./wechat-insight labels
./wechat-insight labels --apply-suggestions
./wechat-insight labels --limit 20
```

标签模板会：
- 只包含私聊联系人
- 保留已有 `role` / `notes`
- 输出 `suggested_role`
- 输出 `suggested_role_reason`
- 输出 `review_priority_score`

`--apply-suggestions` 的规则：
- 只会填充空白 / `unknown` 的 `role`
- 不会覆盖用户已确认标签

#### 7. 用户点名 MBTI / 情绪 / 口癖 / 社交图谱

当前必须明确说明：
- 这些脚本已经可用
- 结果属于启发式分析，不是模型级人格/情绪判断
- 可以直接进入：
  - Markdown 报告
  - `report-data`
  - `html`
  - `dashboard`

---

## 推荐话术与策略

### 用户说“帮我分析下微信”

优先走：
1. `./wechat-insight doctor`
2. 若未配置则 `./wechat-insight setup`
3. 若未明确分析方向，优先推荐：
   - `daily`
   - `customer`

### 用户说“帮我看看最近聊天情况”

优先走：

```bash
./wechat-insight export --days 7
./wechat-insight daily
```

### 用户说“帮我看客户和商机”

优先走：

```bash
./wechat-insight export --days 30
./wechat-insight labels --apply-suggestions
./wechat-insight customer --labels ~/.config/wechat-insight-contacts_labels.json
```

### 用户说“我想做 MBTI / 性格分析”

当前应该回答：
- 可以直接跑 `./wechat-insight mbti`
- 结果是基于聊天表达风格的启发式推测，不是人格测评
- 最好和 `emotion / speech / social / html / dashboard` 一起看，而不是单独解读

---

## 产物目录

### 配置

- `~/.config/wechat-insight.json`
- `~/.config/wechat-keys.json`
- `~/.config/wechat-insight-contacts_labels.json`

### 导出数据

目录：

```text
~/.wechat-insight/data/
```

主要文件：
- `messages_YYYYMMDD_YYYYMMDD.jsonl`
- `export_meta.json`

### feature 层

目录：

```text
~/.wechat-insight/features/
```

主要文件：
- `messages_enriched_*.jsonl`
- `daily_features.jsonl`
- `chat_features.jsonl`
- `contact_features.jsonl`

### 报告

目录：

```text
~/.wechat-insight/reports/
```

主要文件：
- `daily_*.md`
- `customer_report.md`
- `report_payload_*.json`
- `dashboard_*.html`

---

## 关键数据字段

当前导出层已经有这些关键字段：
- `is_self`
- `direction`
- `real_sender_id`

当前 feature 层已经有这些关键衍生字段：
- `message_id`
- `date / hour / weekday`
- `chat_type`
- `content_clean`
- `is_question`
- `is_action_item`
- `is_schedule`
- `is_business_signal`
- `is_quote_signal`
- `is_support_signal`
- `is_negative_signal`
- `topic_tags`
- `emotion_label`

这意味着：
- 日报和商业分析已经有稳定底座
- MBTI / 响应延迟 / 更细社交分析已经接入统一导出链路
- HTML 网页报告已经可以直接生成
- React dashboard 适合作为第二阶段展示层，而不是第一阶段交付物

---

## 联系人标签文件格式

示例：

```json
{
  "contacts": {
    "客户A": {
      "role": "customer",
      "suggested_role": "customer",
      "suggested_role_reason": ["quote_signal", "business_signal"],
      "notes": "已成交客户",
      "review_priority_score": 62,
      "total_messages": 12,
      "inbound_messages": 8,
      "outbound_messages": 4,
      "last_message_at": "2026-04-25 20:55:21",
      "business_signal_count": 2,
      "quote_signal_count": 1,
      "support_signal_count": 0,
      "negative_signal_count": 0
    }
  }
}
```

建议角色：
- `customer`
- `vendor`
- `family`
- `friend`
- `ad`
- `spam`
- `unknown`

---

## 安全声明

- 所有数据只在本地处理
- 不上传任何服务器
- 密钥保存在本地 `~/.config/`
- Frida 只用于首次提取密钥

---

## 结论

当前这个 skill 的真实定位是：

**微信本地分析工作台 v1**

已经成熟可用的主线：
- `doctor`
- `setup`
- `list`
- `export`
- `features`
- `daily`
- `labels`
- `customer`
- `report-data`
- `html`
- `dashboard`
- `emotion`
- `mbti`
- `speech_patterns`
- `social_graph`

已落地的交付层：
- `report-data`：输出统一展示载荷
- `html`：生成本地可打开的静态网页报告
- `dashboard`：启动本地 React dashboard

规划中待落地的交付层：
- React Bits 风格增强
- 更强筛选、时间范围切换、图表交互

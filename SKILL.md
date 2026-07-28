---
name: analyzing-wechat-chats
description: |
  Use when analyzing, exporting, or reporting on WeChat Mac 4.x local chat history on macOS - builds feature layers from exported JSONL data, and generates daily reports, customer insights, contact labels, and a single-file HTML report (a pure-Python narrative slides recap by default).
  触发词：微信分析、分析微信、微信洞察、微信聊天分析、wechat-insight、analyzing-wechat-chats
---

# 分析微信聊天记录 Analyzing WeChat Chats

> **前置依赖**：本 skill 不是自包含的，运行需要 `./wechat-insight` CLI（仓库：https://github.com/caigee-cmd/wechat-insight）。
>
> 触发本 skill 时按以下顺序判断当前 CLI 位置：
> 1. 当前目录有 `wechat-insight` 可执行文件 → 直接用 `./wechat-insight ...`
> 2. `~/.local/share/wechat-insight/wechat-insight` 存在 → `cd ~/.local/share/wechat-insight` 后用 `./wechat-insight ...`
> 3. 都没有 → 提示用户、并提议执行一行安装（macOS only）：
>    ```bash
>    curl -sL https://raw.githubusercontent.com/caigee-cmd/wechat-insight/main/install.sh | bash
>    ```
>    脚本会 clone 仓库到 `~/.local/share/wechat-insight`、创建 venv、安装 Python 依赖。装好后再 `cd` 进去触发本 skill。`./wechat-insight` launcher 会自动使用 `.venv`，不需要手动 `source activate`。

## 总览

这是一个 **本地微信分析工作台 v1**。

当前已经可用的能力：

- feature 层生成
- Markdown 日报
- 面向自动化宿主的一键 digest 日报
- 客户 / 商业分析
- 联系人标签模板生成与自动建议
- 单文件 HTML 报告（默认叙事版滑动年报，纯 Python 渲染，不依赖 Node）
- 可分享的竖版关系画像卡

启发式分析能力（基于聊天文本的统计规则推测，不是医学诊断、心理测评或模型级结论，结果仅供参考）：
- 情绪分析
- MBTI 推测
- 口癖统计
- 社交图谱

---

## 适用条件

- macOS
- 微信 Mac 4.x 已安装并登录过
- Python 3.9+

---

## 核心原则

- **优先使用统一 CLI：`./wechat-insight`**
- 首次使用先跑 `doctor`
- 分析类请求尽量走：
    - `features`
  - `daily`
  - `labels`
  - `customer`
- 对启发式分析能力，必须明确告知“仅供参考”，不要包装成模型级结论

---

## 当前命令面

| 命令 | 作用 | 状态 |
|------|------|------|
| `./wechat-insight doctor` | 检查配置状态 | 可用 |
| `./wechat-insight features` | 生成 feature 层 | 可用 |
| `./wechat-insight daily` | 生成日报 | 可用 |
| `./wechat-insight labels` | 生成联系人标签模板 | 可用 |
| `./wechat-insight customer` | 生成客户 / 商业分析 | 可用 |
| `./wechat-insight unreplied` | 列出最后一条是对方发来、你还没回的会话 | 可用 |
| `./wechat-insight report-data` | 汇总展示层统一 JSON 载荷 | 可用 |
| `./wechat-insight html` | 生成本地可打开的单文件 HTML 报告（默认叙事版滑动年报） | 可用 |
| `./wechat-insight share` | 生成可分享的竖版关系画像卡 | 可用 |
| `./wechat-insight emotion` | 情绪分析（启发式） | 可用 |
| `./wechat-insight mbti` | MBTI 推测（启发式） | 可用 |
| `./wechat-insight speech` | 口癖统计（启发式） | 可用 |
| `./wechat-insight social` | 社交图谱（启发式） | 可用 |

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
4. 自动识别 `wxid` 和数据库路径
5. 生成：
   - `~/.config/wechat-insight.json`

注意：
- 过程中用户需要手动登录微信
- 首次配置通常要 2-3 分钟

### Phase 3: 根据意图选择任务

#### 1. 用户想看有哪些群 / 联系人

```bash
./wechat-insight list
```

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

#### 3.1 用户想让 OpenClaw / 自动化宿主每天推送沟通摘要

本 skill 不负责定时和推送；OpenClaw 负责调度、推送和失败重试。

推荐让自动化宿主每天执行：

```bash
./wechat-insight doctor
./wechat-insight digest --today --stdout
```

执行规则：
- `doctor` 非 0：提示用户先人工执行 `./wechat-insight setup`
- `digest` 返回 0：从 stdout 读取 Markdown，或读取 `DIGEST_REPORT_PATH=...` 指向的文件
- 当天没有消息：`digest` 仍会返回 0，并生成“暂无可分析消息”的日报

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

#### 4.1 用户想看"有没有谁的消息我还没回"

当用户问"有没有没回复的消息 / 谁的私信我漏回了 / 最近哪些会话我没跟进"时，用 `unreplied`，
不要用 `daily` 的待跟进信号——后者只统计命中关键词（商业 / 排期 / 问题等）的消息，
而 `unreplied` 只看会话最后一条的方向，能覆盖"对方最后发了一句没关键词的话、你没回"的场景。

```bash
./wechat-insight unreplied                       # 默认只看私聊，列全部
./wechat-insight unreplied --days 7              # 只看最近 7 天内的未回复
./wechat-insight unreplied --exclude-ad          # 过滤 labels 中 role 为 ad 的营销号
./wechat-insight unreplied --include-groups      # 同时纳入群聊
./wechat-insight unreplied --output ~/un.md      # 同时写入 Markdown 文件
```

要点：
- 判定"未回复"基于完整历史（只看 inbound/outbound，忽略系统消息），你最后回过的会话不会误报。
- 默认只看私聊；群聊用 `--include-groups` 显式纳入。
- 默认列出全部，不截断（与 `daily` 只展示前 5 条不同）。
- `--exclude-ad` 依赖先跑过 `labels --apply-suggestions` 生成的 role 字段；没有标签文件时会优雅跳过、过滤 0 个。
- 每条会附带规则标签（商业 / 问题 / 售后等）作为上下文提示，但不作为过滤条件。

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
- 属于启发式分析（基于聊天文本的统计规则推测，不是医学诊断、心理测评或模型级结论），结果仅供参考
- 可以直接进入：
  - Markdown 报告
  - `report-data`
  - `html`

---

## 推荐话术与策略

### 用户说“帮我分析下微信”

优先走：
1. `./wechat-insight doctor`
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
- 属于启发式分析（基于聊天表达风格的统计规则推测，不是正式人格测评），结果仅供参考
- 最好和 `emotion / speech / social / html` 一起看，而不是单独解读

---

## 产物目录

### 配置

- `~/.config/wechat-insight.json`
- `~/.config/wechat-insight-contacts_labels.json`

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
- HTML 报告已经可以直接生成（默认叙事版滑动年报，纯 Python 渲染）

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

---

## 结论

当前这个 skill 的真实定位是：

**微信本地分析工作台 v1**

已经成熟可用的主线：
- `doctor`
- `features`
- `daily`
- `labels`
- `customer`
- `report-data`
- `html`
- `share`
- `emotion`
- `mbti`
- `speech`
- `social`

已落地的交付层：
- `report-data`：输出统一展示载荷
- `html`：生成本地可打开的单文件 HTML 报告（默认叙事版滑动年报，纯 Python 渲染）
- `share`：生成可分享的竖版关系画像卡

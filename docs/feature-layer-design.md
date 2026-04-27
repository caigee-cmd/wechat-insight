# WeChat Insight Feature Layer 设计稿

## 目标

把当前项目从“消息导出工具”升级为“可复用分析底座”。

核心原则：

- `raw` 层保留事实
- `features` 层沉淀稳定指标
- `reports` 层只消费指标，不直接重新扫原始消息
- 最终交付不只是一份 Markdown，还要有可直接打开的本地 HTML 网页报告
- 规则负责“算”，LLM 负责“写”

---

## 一、目录结构

建议新增如下结构：

```text
scripts/
  export_messages.py
  extract_keys.py
  features/
    __init__.py
    message_schema.py
    message_rules.py
    normalize.py
    aggregate_chat.py
    aggregate_contact.py
    aggregate_daily.py
    build_features.py
  analyze/
    daily.py
    mbti.py
    customer.py
    speech_patterns.py
    emotion.py
    social_graph.py

data/
  raw/                     # 可选，若以后做本地样本调试
docs/
  feature-layer-design.md
```

CLI 建议增加：

- `./wechat-insight features`
- `./wechat-insight daily`
- `./wechat-insight mbti`
- `./wechat-insight customer`
- `./wechat-insight report-data`
- `./wechat-insight html`
- `./wechat-insight dashboard`

---

## 二、数据流

```text
微信数据库
  -> export_messages.py
  -> messages_*.jsonl
  -> features/build_features.py
  -> messages_enriched.jsonl
  -> daily_features.jsonl / chat_features.jsonl / contact_features.jsonl
  -> analyze/daily.py / analyze/mbti.py / analyze/customer.py
  -> report_payload.json
  -> Markdown 报告 / HTML 网页报告 / React dashboard
```

---

## 三、原始消息字段设计

当前 JSONL 已有基础字段，但要补齐可分析字段。

### 3.1 raw message 标准字段

每条消息建议统一为：

```json
{
  "message_id": "msg_xxx",
  "timestamp": 1777037333,
  "datetime": "2026-04-24 21:28:53",
  "date": "2026-04-24",
  "hour": 21,
  "weekday": 4,

  "chat_id": "wxid_xxx",
  "chat_name": "老婆",
  "chat_type": "private",
  "is_group": false,

  "sender_id": "wxid_xxx",
  "sender_name": "老婆",
  "is_self": false,
  "direction": "inbound",

  "content": "我明天到翔安，应该10:00~10:30。",
  "content_clean": "我明天到翔安 应该10:00 10:30",
  "content_length": 18,

  "msg_type": 1,
  "msg_type_label": "text",
  "has_question": false,
  "has_exclamation": false,
  "has_link": false,
  "emoji_count": 0
}
```

### 3.2 必须新增的字段

- `message_id`
- `date`
- `hour`
- `weekday`
- `chat_type`
- `is_self`
- `direction`
- `content_clean`
- `content_length`

### 3.3 字段说明

#### `message_id`

建议由以下信息组合哈希生成：

- `chat_id`
- `timestamp`
- `sender_id`
- `msg_type`
- `content`

目的：

- 去重
- 建立 message_features 关联

#### `is_self`

这是后续 MBTI / 响应速度 / 客户跟进 的基础字段。

优先策略：

- 从微信数据库真实字段判断
- 如果数据库没有直接字段，再回退到规则推断

没有 `is_self`，很多分析都不可靠。

#### `direction`

建议固定值：

- `outbound`
- `inbound`
- `system`

规则：

- `is_self = true` -> `outbound`
- `is_self = false` -> `inbound`
- 系统消息 -> `system`

---

## 四、message_features 设计

原始层只保留事实，特征层负责“打标签”。

### 4.1 输出结构

```json
{
  "message_id": "msg_xxx",
  "is_question": false,
  "is_action_item": true,
  "is_commitment": false,
  "is_schedule": true,
  "is_business_signal": false,
  "is_quote_signal": false,
  "is_support_signal": false,
  "is_negative_signal": false,
  "topic_tags": ["family", "schedule"],
  "keyword_hits": ["明天", "10:00"],
  "emotion_label": "neutral"
}
```

### 4.2 第一版标签列表

建议第一版只做这些：

- `is_question`
- `is_action_item`
- `is_commitment`
- `is_schedule`
- `is_business_signal`
- `is_quote_signal`
- `is_support_signal`
- `is_negative_signal`
- `topic_tags`

不要一开始做太重的 NLP。

---

## 五、聚合表设计

### 5.1 daily_features

一行表示一天总体情况。

```json
{
  "date": "2026-04-24",
  "total_messages": 1692,
  "text_messages": 1164,
  "group_messages": 1508,
  "private_messages": 184,
  "self_messages": 700,
  "other_messages": 992,
  "active_chats": 30,
  "active_contacts": 12,
  "night_messages": 79,
  "top_chat": "小程序互帮互助 4 群",
  "top_contact": "妹妹",
  "peak_hour": 18,
  "action_signal_count": 42,
  "business_signal_count": 16,
  "support_signal_count": 3
}
```

### 5.2 chat_features

一行表示一个会话在某个窗口期的聚合结果。

```json
{
  "chat_id": "xxx",
  "chat_name": "AI编辑器技术讨论",
  "chat_type": "group",
  "total_messages": 192,
  "self_messages": 38,
  "inbound_messages": 154,
  "active_days": 6,
  "last_active_at": "2026-04-25 20:31:55",
  "question_ratio": 0.11,
  "action_signal_count": 13,
  "business_signal_count": 8,
  "support_signal_count": 1,
  "avg_message_length": 19.2
}
```

### 5.3 contact_features

一行表示一个联系人在某个窗口期的画像。

```json
{
  "contact_id": "wxid_xxx",
  "contact_name": "某客户",
  "role": "customer",
  "stage": "negotiating",
  "total_messages_30d": 128,
  "self_messages_30d": 61,
  "inbound_messages_30d": 67,
  "active_days_30d": 11,
  "avg_response_latency_min": 17,
  "request_count": 12,
  "commitment_count": 6,
  "quote_signal_count": 3,
  "support_signal_count": 1,
  "negative_signal_count": 0
}
```

---

## 六、规则词典设计

规则词典建议集中在：

- `scripts/features/message_rules.py`

先纯 Python 常量，不急着单独拆配置文件。

### 6.1 问题类

```python
QUESTION_PATTERNS = [
    "？",
    "?",
    "吗",
    "呢",
    "是不是",
    "能不能",
    "可不可以",
    "要不要",
]
```

命中任意一个，可打 `is_question = True`。

### 6.2 待办 / 行动项

```python
ACTION_PATTERNS = [
    "发我",
    "看下",
    "确认下",
    "跟进",
    "推进",
    "安排",
    "记得",
    "处理一下",
    "回复一下",
]
```

### 6.3 承诺 / 闭环

```python
COMMITMENT_PATTERNS = [
    "我来",
    "我处理",
    "我晚点发",
    "我明天发",
    "我跟进",
    "我安排",
    "收到",
    "已发",
    "搞定",
    "完成",
    "确认了",
]
```

### 6.4 时间 / 日程

```python
SCHEDULE_PATTERNS = [
    "明天",
    "后天",
    "待会",
    "今晚",
    "上午",
    "下午",
    "几点",
    "这周",
    "下周",
    "周一",
    "周二",
]
```

另加正则：

- `\d{1,2}:\d{2}`
- `\d{1,2}点`

### 6.5 商业信号

```python
BUSINESS_PATTERNS = [
    "方案",
    "报价",
    "预算",
    "合同",
    "付款",
    "开票",
    "demo",
    "试用",
    "上线",
    "交付",
]
```

### 6.6 报价信号

```python
QUOTE_PATTERNS = [
    "报价",
    "价格",
    "多少钱",
    "预算",
    "费用",
    "怎么收费",
]
```

### 6.7 售后信号

```python
SUPPORT_PATTERNS = [
    "报错",
    "有问题",
    "不能用",
    "失败了",
    "异常",
    "退款",
    "没反应",
    "崩了",
]
```

### 6.8 负向信号

```python
NEGATIVE_PATTERNS = [
    "烦",
    "急",
    "无语",
    "离谱",
    "不行",
    "不对",
    "不满意",
    "生气",
    "崩溃",
]
```

### 6.9 主题标签词典

建议第一版先做 6 类：

```python
TOPIC_KEYWORDS = {
    "work": ["上线", "需求", "开发", "排期", "接口", "发版", "测试", "修复"],
    "customer": ["报价", "合同", "预算", "方案", "付款", "客户", "合作"],
    "family": ["老婆", "妈妈", "弟弟", "妹妹", "回家", "吃饭"],
    "community": ["群", "社群", "活动", "拉群", "管理员"],
    "leisure": ["吃饭", "电影", "打球", "喝酒", "出去玩"],
    "ai": ["agent", "cursor", "claude", "gpt", "模型", "提示词", "工作流"],
}
```

命中可多标签。

---

## 七、模块职责

### `message_schema.py`

负责：

- 定义原始消息标准字段
- 处理字段默认值
- 做格式校验

### `normalize.py`

负责：

- `content_clean`
- 标点清洗
- 空白符归一化
- URL 清理

### `message_rules.py`

负责：

- 问题、待办、承诺、时间、商业、售后标签识别
- 主题标签命中

输出：

- 单条消息标签字典

### `aggregate_daily.py`

负责：

- 生成 `daily_features`

### `aggregate_chat.py`

负责：

- 生成 `chat_features`

### `aggregate_contact.py`

负责：

- 生成 `contact_features`

### `build_features.py`

负责：

- 读取导出的 `messages_*.jsonl`
- 生成 `messages_enriched.jsonl`
- 调用各聚合器输出 feature 文件

---

## 八、产物文件建议

```text
~/.wechat-insight/data/
  messages_20260424_20260425.jsonl
  export_meta.json

~/.wechat-insight/features/
  messages_enriched_20260424_20260425.jsonl
  daily_features.jsonl
  chat_features.jsonl
  contact_features.jsonl

~/.wechat-insight/reports/
  daily_20260424_20260425.md
  mbti_20260424_20260425.md
  customer_20260424_20260425.md
  report_payload_20260424_20260425.json
  dashboard_20260424_20260425.html
```

---

## 九、HTML 网页报告层设计

目标：

- 分析完成后，输出一个本地可直接打开的 HTML 文件
- 不依赖服务端，不要求启动 Web 服务
- 用户双击或浏览器打开即可查看
- 页面数据来自 `features` 和各分析报告，不重复扫描原始消息

建议命令：

```bash
./wechat-insight report-data
./wechat-insight html
./wechat-insight dashboard
./wechat-insight html --input ~/.wechat-insight/features/*.jsonl
./wechat-insight html --days 30
```

推荐职责：

- `report-data`：把分析结果整理为统一 JSON 载荷，作为展示层唯一输入
- `html`：基于 `report-data` 生成单文件静态 HTML
- `dashboard`：启动本地 React dashboard，仅作为后续增强形态

建议输入优先级：

1. `daily_features.jsonl`
2. `chat_features.jsonl`
3. `contact_features.jsonl`
4. `daily/customer` 分析结果
5. 必要时回退到 `messages_enriched_*.jsonl`

建议页面结构：

- 顶部总览卡片：总消息数、活跃会话数、活跃联系人数、峰值时段、夜间消息占比
- 时间趋势区：每日消息趋势、峰值小时分布
- 会话排行区：最活跃群聊 / 私聊、收发结构拆分
- 客户洞察区：高意向机会、售后风险、待跟进联系人
- 联系人标签区：`customer / vendor / family / friend / unknown` 分布
- 信号明细区：报价、报错、待办、排期、负向信号
- 页尾元信息：分析时间范围、输入文件、生成时间

建议技术方案：

- 第一版优先生成单文件静态 HTML，不先引入 React 工程
- 先沉淀 `report_payload.json`，再决定展示层实现
- 数据直接内嵌到 HTML 的 JSON script block
- 图表优先用轻量前端方案，避免引入复杂框架
- 样式优先本地内联，确保文件可独立分发和打开
- React dashboard 放到后续阶段，不阻塞首版交付
- React Bits 只用于后续展示层增强，不作为第一阶段主依赖
- 后续如需要，再升级为多页面 dashboard 或本地 web app

推荐分层：

```text
analysis
  -> report_payload.json
  -> static html
  -> react dashboard
```

产物定位：

- Markdown 报告适合归档和文本阅读
- HTML 报告适合日常查看、演示和快速浏览
- React dashboard 适合后续做筛选、交互和更强的可视化
- 两者共存，HTML 作为第一优先的最终用户体验层

---

## 十、开发顺序

建议分 7 个阶段：

### Phase 1

- 在 `export_messages.py` 中补 `message_id/date/hour/weekday/chat_type/content_clean/content_length`
- 尽快搞定 `is_self`

### Phase 2

- 新建 `scripts/features/`
- 实现 `message_rules.py`
- 实现 `build_features.py`

### Phase 3

- 升级 `daily.py`
- 从“直接扫原始消息”改成“优先吃 feature 文件”

### Phase 4

- 实现 `customer.py`
- 再做 `mbti.py`

### Phase 5a

- 新增 `report-data` 模块
- 把 `daily/customer/labels/features` 汇总成统一 `report_payload.json`
- 明确 payload schema，避免展示层重复拼装数据

### Phase 5b

- 新增 `html` 报告生成模块
- 基于 `report_payload.json` 输出静态网页
- 第一版先做单页 dashboard
- 保证本地双击即可打开

### Phase 5c

- 新增 `dashboard` 本地前端项目
- 用 React 实现更强交互版 dashboard
- React Bits 仅用于卡片、标题、轻量动效增强
- 不允许 React 工程反向耦合分析脚本

不要反过来。

---

## 十一、当前最关键的技术判断

### 1. `is_self` 是绝对优先级

没有这个字段：

- 响应速度失真
- 主动性失真
- MBTI 失真
- 客户跟进失真

### 2. 商业分析优先于 MBTI

原因：

- 商业标签更容易规则化
- 更容易验证真假
- 对用户价值更直接

### 3. 先做 feature 层，再做图表

否则图表只是把脏统计画漂亮。

### 4. 先做静态 HTML，再做 React dashboard

原因：

- 单文件 HTML 更适合本地打开、归档和分享
- React 工程更适合第二阶段交互增强
- 展示层必须消费统一 payload，而不是直接耦合分析脚本

---

## 十二、建议的下一步实现

下一步建议直接做：

1. `scripts/features/message_rules.py`
2. `scripts/features/build_features.py`
3. `./wechat-insight features`

等 feature 层出来之后，再升级：

1. `daily`
2. `customer`
3. `mbti`
4. `report-data`
5. `html`
6. `dashboard`

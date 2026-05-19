# WeChat Insight

把你的微信聊天记录，变成一个可以本地查看的关系洞察、客户线索和人格画像工作台。

> 一个本地优先的微信分析项目：从聊天记录里看到关系结构、商业机会和表达习惯。

面向 `macOS + 微信 Mac 4.x`，从本地加密数据库提取聊天记录，生成：

- 导出数据和统一特征层
- 日报、客户分析、待跟进信号
- 情绪分析、MBTI 推测、口癖统计、社交图谱（均为启发式分析，仅供参考）
- 本地可打开、内置交互式 React 工作台的单文件 HTML 报告

## 一句话看懂

`WeChat Insight = 微信聊天记录导出 + 分析引擎 + 单文件 HTML 报告（内置交互式工作台）`

它不是单纯“把聊天导出来”，而是把聊天变成一套可以看的洞察结果。

## 效果预览

你最终会得到一份**单文件 HTML 报告**：双击就能开、可以发邮件/微信，里面内联了一个交互式 React 工作台（可筛选、切窗口、看趋势和关系图）。

截图文件统一放在 `docs/screenshots/`，README 里展示的是几个最核心的页面状态。

### 关系工作台总览

![关系工作台总览](docs/screenshots/dashboard-persona-overview.png)

展示报告的主工作台视图：总消息量、覆盖天数、消息结构、人格推测、情绪底色和待跟进数量会被压到同一个决策界面里，适合快速判断这段时间的整体聊天状态。

### 情绪分布（启发式）

![情绪分布](docs/screenshots/dashboard-emotion-distribution.png)

展示高级分析里的情绪结构。属于启发式分析（基于聊天文本的统计规则推测，不是医学诊断、心理测评或模型级结论），结果仅供参考。用来观察表达更偏积极、平稳，还是更容易出现焦虑、愤怒和消极信号。

### MBTI 推测（启发式）

![MBTI 推测](docs/screenshots/dashboard-mbti-profile.png)

展示基于聊天行为反推的四维倾向，包括能量来源、信息偏好、决策方式和行动节奏。属于启发式分析（基于表达风格统计推测，不是正式人格测评），结果仅供参考。

### 待跟进客户

![待跟进客户](docs/screenshots/dashboard-followup-customers.png)

展示客户维度聚合出的待处理项。它会把私聊里的问题、排期、负面反馈和疑似商机集中到一个列表里，方便优先处理最值得继续跟进的人和事。


## 为什么这个项目值得看

- **全本地**：默认不上传云端，数据留在自己机器上
- **链路完整**：从密钥提取、消息导出、特征层、分析层到展示层全部打通
- **可直接分享**：导出单文件 HTML，里面内联了完整的交互式工作台
- **不止做统计**：除了消息量和活跃时段，还会给出客户机会、待跟进、语言风格和关系画像

## 你最终能看到什么

- 哪些群和联系人最活跃
- 你最近的聊天节奏、昼夜分布、响应时延
- 哪些私聊有商业机会、哪些对话值得跟进
- 你的高频表达、口癖和常见说话风格（启发式）
- 基于聊天表达风格的 `MBTI` 和情绪画像（启发式，仅供参考）
- 一份可直接打开的本地网页报告

## 适合谁

- 想分析自己的微信社交结构和聊天节奏
- 想把微信私聊整理成客户线索和待跟进列表
- 想做“个人数据分析 / 数字分身 / 关系画像”类内容分享
- 想把分析结果做成网页、截图展示

## 当前能力

- `doctor`：检查配置状态
- `setup`：首次提取数据库密钥并生成配置
- `list` / `export`：列出会话并导出 JSONL
- `features`：生成统一特征层
- `daily` / `digest` / `customer` / `labels`：日报、一键自动化日报、客户分析、标签模板
- `emotion` / `mbti` / `speech` / `social`：高级画像分析（启发式，仅供参考）
- `report-data`：汇总统一展示载荷
- `html`：生成本地可打开的单文件 HTML 报告（内置交互式 React 工作台）

## 使用边界

- 目前仅支持 `macOS`
- 需要本机已安装并登录过 `微信 Mac 4.x`
- 默认是本地处理，不上传云端
- 请只处理你自己有权处理的数据
- `MBTI / 情绪 / 口癖 / 社交图谱` 属于启发式分析（基于聊天文本的统计规则推测，不是医学诊断、心理测评或模型级结论），结果仅供参考

## 环境要求

- Python `3.9+`
- Node.js `18+`，用于 build HTML 报告中的 React 工作台，`20+` 更稳

## 快速开始

```bash
git clone <your-repo-url>
cd wechat-insight

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

先检查环境：

```bash
./wechat-insight doctor
```

首次提取密钥并生成配置：

```bash
./wechat-insight setup
```

说明：

- `setup` 过程中会尝试自动安装 `frida / frida-tools`
- 过程中需要你手动登录微信
- 默认配置会写到：
  - `~/.config/wechat-insight.json`
  - `~/.config/wechat-keys.json`

导出最近 7 天聊天：

```bash
./wechat-insight export --days 7
```

生成日报和客户分析：

```bash
./wechat-insight daily --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight customer --input ~/.wechat-insight/data/messages_*.jsonl
```

给 OpenClaw / 其他自动化宿主生成当天沟通摘要：

```bash
./wechat-insight digest --today --stdout
```

说明：

- `digest` 会先导出当天消息，再生成 Markdown 日报
- 输出固定包含 `DIGEST_REPORT_PATH=...`，自动化宿主可以读取该文件再推送
- `--stdout` 会同时把 Markdown 正文打印出来，方便直接作为推送内容
- 首次初始化仍需人工执行 `./wechat-insight setup`

生成静态网页报告：

```bash
./wechat-insight html --input ~/.wechat-insight/data/messages_*.jsonl
```

默认会把 `dashboard/` 这个 React 工作台 build + inline 成单文件 HTML；如果需要旧版 Python 静态模板，可以加 `--renderer legacy`。

`html` 命令首次运行会自动跑 `npm install`。如果想提前装好前端依赖加快首次出图：

```bash
cd dashboard
npm install
```

## 常用命令

```bash
./wechat-insight doctor
./wechat-insight setup
./wechat-insight list
./wechat-insight export --days 30
./wechat-insight digest --today --stdout
./wechat-insight features --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight daily --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight customer --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight labels --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight emotion --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight mbti --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight speech --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight social --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight report-data --input ~/.wechat-insight/data/messages_*.jsonl
./wechat-insight html --input ~/.wechat-insight/data/messages_*.jsonl
```

## 输出位置

默认会写到：

- 数据导出：`~/.wechat-insight/data/`
- 特征层：`~/.wechat-insight/features/`
- 报告：`~/.wechat-insight/reports/`

常见产物：

- `messages_*.jsonl`
- `features_*.jsonl`
- `daily_*.md`
- `customer_*.md`
- `emotion_*.md`
- `mbti_*.md`
- `speech_*.md`
- `social_*.md`
- `report_payload_*.json`
- `dashboard_*.html`

## OpenClaw 自动化建议

OpenClaw 负责定时、推送和失败重试；本项目只提供稳定的本地日报生成命令。

推荐任务命令：

```bash
cd /path/to/wechat-insight
./wechat-insight doctor
./wechat-insight digest --today --stdout
```

自动化策略：

- `doctor` 返回非 0 时，提示用户先人工执行 `setup`
- `digest` 返回 0 时，读取 stdout 或 `DIGEST_REPORT_PATH` 对应文件
- 当天没有消息时，`digest` 仍会生成“暂无可分析消息”的日报，避免误报任务失败
- 不要在定时任务里执行 `setup`，因为它需要登录微信和 Frida 注入

## 开发

运行 Python 测试：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

构建 React 工作台（开发用，`html` 命令会自动跑）：

```bash
cd dashboard
npm ci
npm run build
```

## 本机验收

这个项目以真机链路为准，默认不依赖 GitHub CI。

常用本机回归：

```bash
./scripts/local_smoke.sh doctor
./scripts/local_smoke.sh setup
./scripts/local_smoke.sh quick --days 7
```

## 项目结构

```text
wechat-insight/
├── scripts/
│   ├── extract_keys.py
│   ├── export_messages.py
│   ├── features/
│   └── analyze/
├── dashboard/
├── docs/
├── tests/
├── wechat-insight
└── wechat_insight_cli.py
```

## 说明

- HTML 报告内嵌的 React 工作台中，部分动效组件参考并改造自 React Bits
- 当前仓库默认不包含真实聊天数据与真实分析产物

## License

MIT，见 [LICENSE](./LICENSE)

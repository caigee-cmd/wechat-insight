#!/usr/bin/env python3
"""生成一份脱敏的示例聊天数据，用于在线 Demo 和本地试跑。

所有人名、群名、内容都是虚构的，不含任何真实个人信息。数据用固定随机种子
生成，因此每次产出完全一致，方便复现和审计。

用法：
    python3 scripts/make_sample_data.py                       # 写到 docs/sample/messages_sample.jsonl
    python3 scripts/make_sample_data.py -o /tmp/sample.jsonl  # 自定义输出
    python3 scripts/make_sample_data.py --days 30 --seed 7

产物可以直接喂给分析链路：
    ./wechat-insight html --input docs/sample/messages_sample.jsonl
"""

import argparse
import json
import os
import pathlib
import random
from datetime import datetime, timedelta


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "sample" / "messages_sample.jsonl"

SELF_ID = "__self__"
SELF_NAME = "我"

# —— 虚构会话：私聊（含客户/朋友/同事）与群聊 ——
PRIVATE_CHATS = [
    {"id": "demo_lin", "name": "客户·林总", "kind": "customer_warm"},
    {"id": "demo_zhao", "name": "客户·赵工", "kind": "customer_followup"},
    {"id": "demo_qian", "name": "客户·钱姐", "kind": "customer_cold"},
    {"id": "demo_xiaoyu", "name": "同事·小鱼", "kind": "colleague"},
    {"id": "demo_laowang", "name": "老王", "kind": "friend"},
    {"id": "demo_mom", "name": "妈妈", "kind": "family"},
]
GROUP_CHATS = [
    {"id": "demo_proj@chatroom", "name": "智能助手项目对接群", "kind": "work_group"},
    {"id": "demo_roommate@chatroom", "name": "大学寝室四人组", "kind": "social_group"},
    {"id": "demo_family@chatroom", "name": "家庭群", "kind": "family_group"},
]

GROUP_MEMBERS = {
    "demo_proj@chatroom": [("u_pm", "产品-阿May"), ("u_dev", "开发-老陈"), ("u_qa", "测试-丸子")],
    "demo_roommate@chatroom": [("u_r1", "阿强"), ("u_r2", "胖虎"), ("u_r3", "眼镜")],
    "demo_family@chatroom": [("u_dad", "爸爸"), ("u_mom", "妈妈"), ("u_sis", "妹妹")],
}

# —— 按会话类型准备的对白模板 ——
# inbound = 对方发来, outbound = 我发出。口头禅刻意重复，方便口癖分析出信号。
INBOUND = {
    "customer_warm": [
        "你好，方案我看过了，整体挺满意的！",
        "说实话这版报价我们能接受，准备走流程了。",
        "对了，能不能这周五之前把合同发我？",
        "感谢感谢，配合得很愉快～",
        "还有个小问题，交付周期能压到两周吗？",
    ],
    "customer_followup": [
        "上次说的接口文档发我一份呗？",
        "这个事我得跟领导再确认下，稍等。",
        "emmm 价格还是有点超预算了。",
        "你看下周二方便对一下需求吗？",
        "在吗？那个排期表麻烦更新一下。",
    ],
    "customer_cold": [
        "我们暂时先不考虑了，谢谢。",
        "说实话这个效果没达到我们预期。",
        "预算这块卡得比较死，可能没法推进。",
        "先放着吧，有需要再联系你。",
    ],
    "colleague": [
        "这个 bug 我先看看，稍等哈。",
        "周报你那块写完了吗？我催一下。",
        "说真的这需求改得有点频繁了哈哈。",
        "好的好的，我这就改。",
        "今天加班吗？要不要一起点个饭。",
    ],
    "friend": [
        "周末爬山不？天气贼好。",
        "哈哈哈你那表情包给我发一个。",
        "最近咋样，好久没聚了。",
        "说实话我也emo了，工作太累。",
        "晚上开黑不？",
    ],
    "family": [
        "记得按时吃饭，别老熬夜。",
        "周末回家吗？给你包饺子。",
        "天冷了多穿点。",
        "钱够不够花，不够跟妈说。",
    ],
    "work_group": [
        "@所有人 今天下班前同步下进度哈。",
        "这个接口联调过了，可以测了。",
        "测试发现一个阻塞问题，麻烦看下。",
        "排期我更新到文档了，大家确认。",
        "明天上午十点拉个会对齐需求。",
    ],
    "social_group": [
        "哈哈哈哈笑死，谁还记得当年那事。",
        "啥时候搞个聚会啊，想你们了。",
        "刚抢到票，五一一起出去玩！",
        "说真的这群该改名了哈哈。",
    ],
    "family_group": [
        "今晚视频啊，妈想你了。",
        "明天降温，记得加衣。",
        "周末家庭聚餐定在中午十二点。",
    ],
}
OUTBOUND = {
    "customer_warm": [
        "好嘞！我今天就把合同整理好发您。",
        "没问题，交付这块我帮您盯着，放心。",
        "感谢林总信任，咱们尽快推进～",
        "收到，方案细节我再优化一版。",
    ],
    "customer_followup": [
        "好的，接口文档我下午整理给您。",
        "明白，那我等您内部确认的结果。",
        "价格我帮您再申请一下折扣空间。",
        "排期表我现在就更新，稍等。",
    ],
    "customer_cold": [
        "理解的，那我先不打扰，后续有进展随时找我。",
        "好的，感谢您抽时间沟通。",
    ],
    "colleague": [
        "辛苦啦，那块我已经提交了。",
        "好的好的，那我先去改这个。",
        "哈哈确实，需求又变了。",
        "行，那晚上一起吃。",
    ],
    "friend": [
        "爬山可以啊，周六约起！",
        "哈哈哈这就给你发。",
        "确实好久没聚了，找个周末。",
        "晚上开黑，等我下班。",
    ],
    "family": [
        "知道啦妈，我会注意的。",
        "周末回，想吃饺子！",
        "放心，钱够花的。",
    ],
    "work_group": [
        "我这边接口已就绪，可联调。",
        "收到，阻塞问题我优先处理。",
        "确认，明天十点的会我准时到。",
    ],
    "social_group": [
        "哈哈哈这必须聚一波！",
        "五一算我一个！",
        "想你们了，安排上。",
    ],
    "family_group": [
        "好的，今晚视频。",
        "收到，会加衣服的。",
        "中午十二点，准时到。",
    ],
}

# 少量非文本消息，让消息结构更真实
NON_TEXT = [
    (3, "image", "[image]"),
    (47, "sticker", "[sticker]"),
    (34, "voice", "[voice]"),
    (49, "link", "[link] 一篇关于时间管理的文章"),
]


def pick(rng, items):
    return items[rng.randrange(len(items))]


def make_record(ts, chat, sender_id, sender_name, content, msg_type, label, is_group, is_self):
    direction = "outbound" if is_self else "inbound"
    return {
        "timestamp": int(ts),
        "datetime": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
        "chat_id": chat["id"],
        "chat_name": chat["name"],
        "msg_type": msg_type,
        "msg_type_label": label,
        "is_group": is_group,
        "real_sender_id": sender_id,
        "is_self": is_self,
        "direction": direction,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "content": content,
    }


def generate(days, seed, anchor=None):
    rng = random.Random(seed)
    records = []
    # 固定锚点日期，保证"种子固定 -> 产物完全一致"，提交的样例/Demo 不会每天漂移。
    end = (anchor or datetime(2026, 5, 25, 22, 0, 0))
    start = end - timedelta(days=days - 1)

    for day_offset in range(days):
        day = start + timedelta(days=day_offset)
        # 工作日更活跃；偶尔有几天几乎不聊（更真实）
        is_weekend = day.weekday() >= 5
        if rng.random() < 0.08:
            continue  # 安静的一天

        # 私聊
        for chat in PRIVATE_CHATS:
            kind = chat["kind"]
            # 客户类只在工作日活跃，家人/朋友周末更多
            if kind.startswith("customer") and is_weekend and rng.random() < 0.7:
                continue
            if rng.random() < 0.45:
                continue
            n_turns = rng.randint(1, 3)
            base_hour = rng.randint(9, 21)
            t = day.replace(hour=base_hour, minute=rng.randint(0, 59))
            for _ in range(n_turns):
                # 对方先说
                t += timedelta(minutes=rng.randint(2, 40))
                if rng.random() < 0.12:
                    mt, label, body = pick(rng, NON_TEXT)
                    records.append(make_record(t.timestamp(), chat, chat["id"], chat["name"], body, mt, label, False, False))
                else:
                    body = pick(rng, INBOUND[kind])
                    records.append(make_record(t.timestamp(), chat, chat["id"], chat["name"], body, 1, "text", False, False))
                # 我回复（冷客户有时不回）
                if kind == "customer_cold" and rng.random() < 0.4:
                    continue
                t += timedelta(minutes=rng.randint(1, 25))
                body = pick(rng, OUTBOUND[kind])
                records.append(make_record(t.timestamp(), chat, SELF_ID, SELF_NAME, body, 1, "text", False, True))

        # 群聊
        for chat in GROUP_CHATS:
            kind = chat["kind"]
            if kind == "work_group" and is_weekend and rng.random() < 0.8:
                continue
            if rng.random() < 0.5:
                continue
            members = GROUP_MEMBERS[chat["id"]]
            n_msgs = rng.randint(2, 6)
            t = day.replace(hour=rng.randint(9, 22), minute=rng.randint(0, 59))
            for _ in range(n_msgs):
                t += timedelta(minutes=rng.randint(1, 30))
                if rng.random() < 0.3:
                    body = pick(rng, OUTBOUND[kind])
                    records.append(make_record(t.timestamp(), chat, SELF_ID, SELF_NAME, body, 1, "text", True, True))
                else:
                    mid, mname = pick(rng, members)
                    body = pick(rng, INBOUND[kind])
                    records.append(make_record(t.timestamp(), chat, mid, mname, body, 1, "text", True, False))

    # —— 注入几条"未回复的开口线索"，让"待跟进客户"功能在 Demo 里有内容 ——
    # 关键词刻意命中提问 / 报价 / 负面信号；时间戳放在全局最晚之后，确保这是
    # 该会话最后一条且我没有再回复，从而被判定为待跟进。
    latest_ts = max((r["timestamp"] for r in records), default=int(end.timestamp()))
    open_threads = [
        ("demo_zhao", "客户·赵工", "那个报价单你今天能发我吗？我等着上会。"),
        ("demo_qian", "客户·钱姐", "说实话这版方案我不太满意，价格也不行，再想想。"),
        ("demo_lin", "客户·林总", "合同里的交付时间能不能再帮我确认一下？"),
    ]
    for offset, (cid, cname, body) in enumerate(open_threads):
        chat = {"id": cid, "name": cname}
        ts = latest_ts + 600 + offset * 120
        records.append(
            make_record(ts, chat, cid, cname, body, 1, "text", False, False)
        )

    records.sort(key=lambda r: r["timestamp"])
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成脱敏示例聊天数据")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT), help="输出 JSONL 路径")
    parser.add_argument("--days", type=int, default=30, help="覆盖天数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（固定以便复现）")
    args = parser.parse_args(argv)

    records = generate(args.days, args.seed)
    out_path = pathlib.Path(os.path.expanduser(args.output))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"已生成 {len(records)} 条脱敏示例消息 -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

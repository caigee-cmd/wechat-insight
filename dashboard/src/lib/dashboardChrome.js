export function buildMetricCards(overview) {
  return [
    { label: "总消息", value: overview.total_messages || 0, tone: "ink", detail: "全量会话脉冲" },
    { label: "文本消息", value: overview.text_messages || 0, tone: "sea", detail: "可解析语义样本" },
    { label: "活跃会话", value: overview.active_chat_count || 0, tone: "gold", detail: "本周期触达范围" },
    { label: "私聊联系人", value: overview.total_private_contacts || 0, tone: "ink", detail: "一对一关系池" },
    { label: "商机联系人", value: overview.business_contact_count || 0, tone: "sea", detail: "高意向客群" },
    { label: "待跟进", value: overview.pending_followup_count || 0, tone: "gold", detail: "需要继续推进" },
  ];
}

export function buildHeroRows({ emotionLabel, emotionTone, mbtiType, overviewDays }) {
  return [
    ["观察区间", `${overviewDays} 天`, "ink"],
    ["人格推测", mbtiType || "--", "sea"],
    ["情绪底色", emotionLabel, emotionTone],
  ];
}

export function buildOrbitRows({ avgMessageLength, groupMessageCount, medianResponseText, privateMessageCount }) {
  return [
    ["群聊消息", groupMessageCount],
    ["私聊消息", privateMessageCount],
    ["平均长度", avgMessageLength],
    ["中位响应", medianResponseText],
  ];
}

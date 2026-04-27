import { formatDisplayDateTime, formatStageLabel } from "./presentation.js";

function compactDateTime(value) {
  const formatted = formatDisplayDateTime(value);
  return formatted === "--" ? "时间未知" : formatted;
}

function formatPercent(value) {
  const number = Number(value);
  if (Number.isNaN(number)) {
    return "--";
  }
  return `${(number * 100).toFixed(1)}%`;
}

function formatMinutes(value) {
  const number = Number(value);
  if (Number.isNaN(number)) {
    return "--";
  }
  return `${number.toFixed(2).replace(/\.?0+$/, "")} 分钟`;
}

export function buildSignalsSnapshot({
  customerFollowups = [],
  dailyFollowups = [],
  topOpportunities = [],
  topRisks = [],
}) {
  const firstFollowup = dailyFollowups[0];
  const firstOpportunity = topOpportunities[0];
  const firstRisk = topRisks[0];
  const firstCustomerFollowup = customerFollowups[0];

  return {
    headline: firstFollowup
      ? `先处理 ${firstFollowup.chat_name || "当前待跟进对象"}，再推进高分机会和售后风险。`
      : "先从最高分机会和待跟进客户开始推进。",
    cards: [
      {
        label: "最该先回",
        value: firstFollowup?.chat_name || "--",
        detail: firstFollowup
          ? `${(firstFollowup.labels || []).join(" / ") || "待跟进"} · ${compactDateTime(firstFollowup.datetime)}`
          : "暂无待跟进会话",
      },
      {
        label: "商机最高",
        value: firstOpportunity?.contact_name || "--",
        detail: firstOpportunity
          ? `机会分 ${firstOpportunity.opportunity_score || 0} · ${formatStageLabel(firstOpportunity.stage)}`
          : "暂无明显商业机会",
      },
      {
        label: "风险最高",
        value: firstRisk?.contact_name || "--",
        detail: firstRisk
          ? `风险分 ${firstRisk.risk_score || 0} · ${formatStageLabel(firstRisk.stage)}`
          : "暂无明显售后风险",
      },
      {
        label: "客户待办",
        value: firstCustomerFollowup?.contact_name || "--",
        detail: firstCustomerFollowup?.pending_followup
          ? `${(firstCustomerFollowup.pending_followup.labels || []).join(" / ") || "待跟进"} · ${compactDateTime(firstCustomerFollowup.pending_followup.datetime)}`
          : "暂无客户级待办",
      },
    ],
  };
}

export function buildPersonaSnapshot({
  overview = {},
  social = {},
  speech = {},
  topEmotionalChats = [],
}) {
  const topPhrase = (speech.repeated_phrases || [])[0];
  const topEmotionalChat = topEmotionalChats[0];
  const mbtiType = overview.mbti_type || "--";
  const emotionLabel = {
    positive: "积极",
    negative: "消极",
    anxious: "焦虑",
    angry: "愤怒",
    neutral: "平稳",
    unknown: "未知",
  }[overview.dominant_emotion] || overview.dominant_emotion || "未知";

  return {
    headline: topEmotionalChat
      ? `${mbtiType} 的执行感很强，情绪整体平稳，但有一个明显的负载源。`
      : `${mbtiType} 的执行感很强，当前画像更偏稳定输出。`,
    cards: [
      {
        label: "人格定调",
        value: `${mbtiType} / ${emotionLabel}`,
        detail: "当前主导人格与情绪底色",
      },
      {
        label: "最高频短语",
        value: topPhrase?.text || "--",
        detail: topPhrase ? `重复 ${topPhrase.count || 0} 次` : "暂无明显重复表达",
      },
      {
        label: "情绪负载源",
        value: topEmotionalChat?.chat_name || "--",
        detail: topEmotionalChat ? `情绪分 ${topEmotionalChat.emotion_score || 0}` : "暂无明显负载会话",
      },
      {
        label: "沟通节奏",
        value: formatMinutes(social.median_response_latency_minutes),
        detail: `夜间占比 ${formatPercent(social.night_message_ratio || 0)}`,
      },
    ],
  };
}

const GROUP_NODE_COLOR = "#2bd4bf";
const CONTACT_NODE_COLOR = "#f5b546";
const GROUP_LINE_COLOR = "#4fd7c7";
const CONTACT_LINE_COLOR = "#e0a646";
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

const EMOTION_LABELS = {
  positive: "积极",
  negative: "消极",
  anxious: "焦虑",
  angry: "愤怒",
  neutral: "平稳",
  unknown: "未知",
};

function formatNumber(value, digits = 0) {
  const number = Number(value);
  if (Number.isNaN(number)) {
    return value ?? "--";
  }
  if (digits > 0) {
    return number.toFixed(digits).replace(/\.?0+$/, "");
  }
  if (Number.isInteger(number)) {
    return String(number);
  }
  return number.toFixed(2).replace(/\.?0+$/, "");
}

function formatPercent(value) {
  const number = Number(value);
  if (Number.isNaN(number)) {
    return value ?? "--";
  }
  return `${(number * 100).toFixed(1)}%`;
}

function emotionLabel(value) {
  return EMOTION_LABELS[value] || value || "未知";
}

export function createSpherePoint({ band, count, index, radius }) {
  const progress = count <= 1 ? 0.5 : (index + 0.5) / count;
  const theta = index * GOLDEN_ANGLE + (band === "contact" ? Math.PI / 6 : -Math.PI / 10);
  const phiMin = band === "group" ? Math.PI * 0.24 : Math.PI * 0.56;
  const phiMax = band === "group" ? Math.PI * 0.46 : Math.PI * 0.78;
  const phi = phiMin + progress * (phiMax - phiMin);

  return {
    x: radius * Math.sin(phi) * Math.cos(theta),
    y: radius * Math.cos(phi),
    z: radius * Math.sin(phi) * Math.sin(theta),
  };
}

function buildDefaultState({ overview, social }) {
  return {
    eyebrow: "Sphere Network",
    title: "将鼠标移到球体节点上",
    subtitle: `${overview?.mbti_type || "未知"} / ${emotionLabel(overview?.dominant_emotion)}`,
    summary: `${formatNumber(overview?.total_messages || 0)} 条消息 · ${formatNumber(social?.median_response_latency_minutes ?? "--", 2)} 分钟响应`,
    type: "会话中心",
    messages: formatNumber(overview?.total_messages || 0),
    business: formatNumber(overview?.business_contact_count || 0),
    support: formatNumber(social?.private_message_count || 0),
    activeDays: formatNumber(overview?.date_span_days || 0),
    selfRatio: "总览视角",
    theme: "center",
  };
}

function buildNodeState(row, theme, type, subtitle, summary) {
  return {
    eyebrow: theme === "group" ? "Group Orbit" : "Contact Orbit",
    title: row.chat_name || row.contact_name || "未知节点",
    subtitle,
    summary,
    type,
    messages: formatNumber(row.total_messages || 0),
    business: formatNumber(row.business_signal_count || 0),
    support: formatNumber(row.support_signal_count || 0),
    activeDays: formatNumber(row.active_days || 0),
    selfRatio: formatPercent(row.self_ratio || 0),
    theme,
  };
}

function buildNode(row, { index, count, radius, maxValue, band }) {
  const totalMessages = Number(row.total_messages || 0);
  const ratio = Math.max(0.16, totalMessages / maxValue);
  const position = createSpherePoint({ band, count, index, radius });
  const isGroup = band === "group";
  const title = row.chat_name || row.contact_name || "未知节点";
  const subtitle = isGroup
    ? `${formatNumber(totalMessages)} 条消息 · 群聊场`
    : `${formatNumber(totalMessages)} 条私聊 · 一对一关系`;
  const summary = isGroup
    ? `活跃 ${formatNumber(row.active_days || 0)} 天 · 平均 ${formatNumber(row.avg_message_length || 0, 2)} 字 · 最近 ${row.last_active_at || "未知"}`
    : `活跃 ${formatNumber(row.active_days || 0)} 天 · 提问占比 ${formatPercent(row.question_ratio || 0)} · 自发 ${formatPercent(row.self_ratio || 0)}`;

  return {
    id: row.chat_id || row.contact_id || `${band}-${index}`,
    key: row.chat_id || row.contact_id || `${band}-${index}`,
    title,
    kind: band,
    theme: isGroup ? "group" : "contact",
    color: isGroup ? GROUP_NODE_COLOR : CONTACT_NODE_COLOR,
    lineColor: isGroup ? GROUP_LINE_COLOR : CONTACT_LINE_COLOR,
    position,
    size: 0.16 + ratio * 0.18,
    haloScale: 1.45 + ratio * 0.34,
    lineOpacity: 0.22 + ratio * 0.58,
    curveLift: (isGroup ? 0.28 : -0.28) + (ratio - 0.16) * (isGroup ? 0.18 : -0.18),
    motionPhase: index * 0.72 + (isGroup ? 0.4 : 1.1),
    row,
    state: buildNodeState(row, isGroup ? "group" : "contact", isGroup ? "高频群聊" : "高频私聊", subtitle, summary),
  };
}

export function buildRelationshipSphereModel({
  chatRows,
  contactRows,
  overview,
  social,
  limit = 6,
  radius = 1.92,
}) {
  const groups = (chatRows || []).filter((row) => row.chat_type === "group").slice(0, limit);
  const contacts = (contactRows || []).slice(0, limit);
  const groupMax = Math.max(...groups.map((row) => Number(row.total_messages || 0)), 1);
  const contactMax = Math.max(...contacts.map((row) => Number(row.total_messages || 0)), 1);

  return {
    radius,
    defaultState: buildDefaultState({ overview, social }),
    nodes: [
      ...groups.map((row, index) =>
        buildNode(row, {
          index,
          count: groups.length,
          radius,
          maxValue: groupMax,
          band: "group",
        })
      ),
      ...contacts.map((row, index) =>
        buildNode(row, {
          index,
          count: contacts.length,
          radius,
          maxValue: contactMax,
          band: "contact",
        })
      ),
    ],
  };
}

import { useInView } from "motion/react";
import { useEffect, useRef, useState } from "react";

const EMOTION_LABELS = {
  positive: "积极",
  negative: "消极",
  anxious: "焦虑",
  angry: "愤怒",
  neutral: "平稳",
  unknown: "未知",
};

const EMOTION_COLORS = {
  positive: "#0f766e",
  negative: "#b45309",
  anxious: "#dc6803",
  angry: "#b42318",
  neutral: "#17313e",
};

const PHRASE_FLOW_LAYOUT_PRESETS = [
  { accent: "sea", x: 14, y: 33, width: 27, mobileSpan: 2, driftX: -10, driftY: -6, rotate: -1.8 },
  { accent: "ink", x: 60, y: 29, width: 24, mobileSpan: 2, driftX: 8, driftY: 2, rotate: 1.4 },
  { accent: "gold", x: 26, y: 6, width: 21, mobileSpan: 1, driftX: -5, driftY: 5, rotate: -0.9 },
  { accent: "sea", x: 55, y: 63, width: 27, mobileSpan: 2, driftX: 6, driftY: -5, rotate: 1.1 },
  { accent: "ink", x: 2, y: 59, width: 21, mobileSpan: 1, driftX: -8, driftY: 4, rotate: -1.2 },
  { accent: "gold", x: 76, y: 8, width: 17, mobileSpan: 1, driftX: 5, driftY: -4, rotate: 1.2 },
  { accent: "sea", x: 34, y: 76, width: 18, mobileSpan: 1, driftX: -4, driftY: 6, rotate: -0.7 },
  { accent: "ink", x: 43, y: 0, width: 18, mobileSpan: 1, driftX: 7, driftY: -3, rotate: 0.8 },
  { accent: "gold", x: 81, y: 48, width: 15, mobileSpan: 1, driftX: 6, driftY: 5, rotate: -0.6 },
  { accent: "sea", x: 7, y: 13, width: 15, mobileSpan: 1, driftX: -3, driftY: 4, rotate: 0.9 },
  { accent: "ink", x: 23, y: 56, width: 17, mobileSpan: 1, driftX: 4, driftY: -5, rotate: 0.5 },
  { accent: "gold", x: 63, y: 80, width: 17, mobileSpan: 1, driftX: -5, driftY: 4, rotate: -0.8 },
];

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

function emotionTone(value) {
  return (
    {
      positive: "sea",
      negative: "gold",
      anxious: "gold",
      angry: "rose",
      neutral: "ink",
    }[value] || "ink"
  );
}

function clipText(value, limit = 22) {
  const text = String(value || "").trim();
  if (text.length <= limit) {
    return text;
  }
  return `${text.slice(0, limit - 1)}…`;
}

function spreadAngles(start, end, count) {
  if (!count) {
    return [];
  }
  if (count === 1) {
    return [(start + end) / 2];
  }
  const step = (end - start) / (count - 1);
  return Array.from({ length: count }, (_, index) => start + step * index);
}

function polarPoint(cx, cy, radius, degrees) {
  const radians = (degrees * Math.PI) / 180;
  return {
    x: cx + Math.cos(radians) * radius,
    y: cy + Math.sin(radians) * radius,
  };
}

function shouldMountDeferredBlock({ hasEnteredViewport, hasMounted, isActiveTab }) {
  return isActiveTab && (hasEnteredViewport || hasMounted);
}

function BarList({ items, suffix, emptyText }) {
  if (!items.length) {
    return <div className="empty-state">{emptyText}</div>;
  }

  const maxValue = Math.max(...items.map((item) => Number(item[1]) || 0), 1);
  return (
    <ul className="bar-list">
      {items.map(([name, value]) => {
        const safeValue = Number(value) || 0;
        const width = Math.max(8, Math.round((safeValue / maxValue) * 100));
        return (
          <li className="bar-list__item" key={`${name}-${value}`}>
            <div className="bar-list__header">
              <span>{name}</span>
              <strong>
                {safeValue}
                {suffix}
              </strong>
            </div>
            <div className="bar-list__track">
              <span className="bar-list__fill" style={{ width: `${width}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function BulletList({ items, emptyText }) {
  if (!items.length) {
    return <div className="empty-state">{emptyText}</div>;
  }
  return (
    <ul className="bullet-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function SignalList({ items, emptyText, renderBody }) {
  if (!items.length) {
    return <div className="empty-state">{emptyText}</div>;
  }
  return <ul className="signal-list">{items.map(renderBody)}</ul>;
}

function MetaList({ rows, emptyText }) {
  const filteredRows = rows.filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!filteredRows.length) {
    return <div className="empty-state">{emptyText}</div>;
  }
  return (
    <ul className="meta-list">
      {filteredRows.map(([label, value]) => (
        <li className="meta-list__item" key={label}>
          <span>{label}</span>
          <code>{String(value)}</code>
        </li>
      ))}
    </ul>
  );
}

function TrendChart({ rows, metricKey, emptyText, accent, title }) {
  if (!rows.length) {
    return <div className="empty-state">{emptyText}</div>;
  }

  const width = 640;
  const height = 220;
  const padding = 24;
  const values = rows.map((row) => Number(row?.[metricKey]) || 0);
  const maxValue = Math.max(...values, 1);
  const stepX = rows.length === 1 ? 0 : (width - padding * 2) / (rows.length - 1);
  const points = rows.map((row, index) => {
    const value = Number(row?.[metricKey]) || 0;
    const x = padding + stepX * index;
    const y = height - padding - ((height - padding * 2) * value) / maxValue;
    return { x, y, value, label: row.date || String(index) };
  });
  const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");
  const areaPoints = [
    `${points[0].x},${height - padding}`,
    ...points.map((point) => `${point.x},${point.y}`),
    `${points[points.length - 1].x},${height - padding}`,
  ].join(" ");

  return (
    <div className={`trend-chart trend-chart--${accent}`}>
      <div className="trend-chart__meta">
        <span>{title}</span>
        <strong>{maxValue}</strong>
      </div>
      <svg className="trend-chart__svg" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
        <defs>
          <linearGradient id={`gradient-${accent}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.38" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <polyline className="trend-chart__area" fill={`url(#gradient-${accent})`} points={areaPoints} />
        <polyline className="trend-chart__line" fill="none" points={polyline} />
        {points.map((point) => (
          <circle className="trend-chart__dot" cx={point.x} cy={point.y} key={`${point.label}-${point.value}`} r="4" />
        ))}
      </svg>
      <div className="trend-chart__labels">
        {rows.map((row) => (
          <span key={row.date}>{row.date?.slice(5) || "--"}</span>
        ))}
      </div>
    </div>
  );
}

function SummaryGrid({ rows }) {
  return (
    <div className="summary-grid">
      {rows.map(([label, value, tone]) => (
        <div className={`summary-chip summary-chip--${tone}`} key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function SectionKicker({ title, subtitle }) {
  return (
    <div className="section-kicker">
      <span className="section-kicker__title">{title}</span>
      <span className="section-kicker__subtitle">{subtitle}</span>
    </div>
  );
}

function StoryDeck({ rows }) {
  if (!rows.length) {
    return <div className="empty-state">暂无日级特征数据</div>;
  }
  return (
    <div className="story-deck">
      {rows.map((row) => (
        <article className="story-card" key={row.date}>
          <div className="story-card__date">{row.date}</div>
          <div className="story-card__value">{formatNumber(row.total_messages)}</div>
          <div className="story-card__meta">
            峰值 {row.peak_hour ?? "--"} 时 · 活跃会话 {formatNumber(row.active_chats)}
          </div>
          <div className="story-card__body">{clipText(row.top_chat || "未知会话", 24)}</div>
        </article>
      ))}
    </div>
  );
}

function EmotionDonut({ distribution }) {
  const rows = [
    ["积极", distribution?.positive || 0, EMOTION_COLORS.positive],
    ["平稳", distribution?.neutral || 0, EMOTION_COLORS.neutral],
    ["消极", distribution?.negative || 0, EMOTION_COLORS.negative],
    ["焦虑", distribution?.anxious || 0, EMOTION_COLORS.anxious],
    ["愤怒", distribution?.angry || 0, EMOTION_COLORS.angry],
  ].filter(([, value]) => Number(value) > 0);
  const total = rows.reduce((sum, [, value]) => sum + Number(value), 0);

  if (!total) {
    return <div className="empty-state">暂无情绪数据</div>;
  }

  let offset = 0;
  const gradient = `conic-gradient(${rows
    .map(([, value, color]) => {
      const start = (offset / total) * 360;
      offset += Number(value);
      const end = (offset / total) * 360;
      return `${color} ${start}deg ${end}deg`;
    })
    .join(", ")})`;

  return (
    <div className="donut-layout">
      <div className="donut">
        <div className="donut__ring" style={{ background: gradient }} />
        <div className="donut__core">
          <strong>{total}</strong>
          <span>情绪样本</span>
        </div>
      </div>
      <ul className="legend-list">
        {rows.map(([label, value, color]) => (
          <li className="legend-list__item" key={label}>
            <span className="legend-list__swatch" style={{ background: color }} />
            <span className="legend-list__label">{label}</span>
            <strong>{value}</strong>
            <em>{Math.round((Number(value) / total) * 100)}%</em>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DimensionMatrix({ dimensions }) {
  const order = ["EI", "SN", "TF", "JP"];
  const cards = order
    .map((key) => {
      const item = dimensions?.[key];
      if (!item) {
        return null;
      }
      const scores = item.scores || {};
      const letters = Object.keys(scores);
      const leftLetter = letters[0] || item.letter || "?";
      const rightLetter = letters[1] || "·";
      const leftScore = Number(scores[leftLetter] ?? 1);
      const rightScore = Number(scores[rightLetter] ?? 0);
      const total = Math.max(leftScore + rightScore, 1);
      const confidence = Math.round(Number(item.confidence || 0) * 100);
      return {
        key,
        label: item.label || key,
        letter: item.letter || "?",
        leftLetter,
        rightLetter,
        leftScore,
        rightScore,
        leftWidth: Math.round((leftScore / total) * 100),
        rightWidth: 100 - Math.round((leftScore / total) * 100),
        confidence,
      };
    })
    .filter(Boolean);

  if (!cards.length) {
    return <div className="empty-state">暂无 MBTI 数据</div>;
  }

  return (
    <div className="dimension-grid">
      {cards.map((item) => (
        <article className="dimension-card" key={item.key}>
          <div className="dimension-card__head">
            <span>{item.label}</span>
            <strong>{item.letter}</strong>
          </div>
          <div className="dimension-card__meta">
            <span>
              {item.leftLetter} {item.leftScore}
            </span>
            <span>置信度 {item.confidence}%</span>
            <span>
              {item.rightLetter} {item.rightScore}
            </span>
          </div>
          <div className="dimension-card__track">
            <span className="dimension-card__fill dimension-card__fill--left" style={{ width: `${item.leftWidth}%` }} />
            <span className="dimension-card__fill dimension-card__fill--right" style={{ width: `${item.rightWidth}%` }} />
          </div>
        </article>
      ))}
    </div>
  );
}

function PhraseCloud({ items }) {
  const rows = [...(items || [])]
    .filter((item) => String(item?.text || "").trim())
    .sort((left, right) => Number(right?.count || 0) - Number(left?.count || 0))
    .slice(0, 12);
  if (!rows.length) {
    return <div className="empty-state">暂无明显重复口癖</div>;
  }
  const maxCount = Math.max(...rows.map((item) => Number(item.count || 1)), 1);

  return (
    <div aria-label="口癖排版云" className="phrase-cloud">
      <svg aria-hidden="true" className="phrase-cloud__paths" viewBox="0 0 100 100" preserveAspectRatio="none">
        <path d="M2 22 C 18 12, 30 14, 43 26 S 72 40, 98 18" />
        <path d="M0 50 C 18 40, 31 43, 42 50 S 70 60, 100 48" />
        <path d="M5 82 C 22 72, 36 68, 46 66 S 73 72, 94 84" />
        <ellipse cx="50" cy="48" rx="15.5" ry="12.5" />
      </svg>
      <div aria-hidden="true" className="phrase-cloud__guides">
        <span />
        <span />
        <span />
      </div>
      <div aria-hidden="true" className="phrase-cloud__core">
        <span>Phrase Flow</span>
        <strong>词语流场</strong>
        <small>高频表达围绕中轴反复折返</small>
      </div>
      {rows.map((item, index) => {
        const count = Number(item.count || 1);
        const normalized = count / maxCount;
        const size = 0.98 + normalized * 0.9;
        const weight = 540 + Math.round(normalized * 180);
        const preset = PHRASE_FLOW_LAYOUT_PRESETS[index % PHRASE_FLOW_LAYOUT_PRESETS.length];
        return (
          <article
            className={`phrase-chip phrase-chip--${preset.accent}`}
            key={`${item.text}-${item.count}`}
            style={{
              "--x": `${preset.x}%`,
              "--y": `${preset.y}%`,
              "--width": `${preset.width}%`,
              "--span-mobile": preset.mobileSpan,
              "--drift-x": `${preset.driftX}px`,
              "--drift-y": `${preset.driftY}px`,
              "--rotate": `${preset.rotate}deg`,
              "--duration": `${(7.2 + index * 0.45).toFixed(2)}s`,
              "--delay": `${(-index * 0.52).toFixed(2)}s`,
              fontSize: `${size}rem`,
            }}
          >
            <span className="phrase-chip__label" style={{ fontWeight: weight }}>
              {item.text}
            </span>
            <span aria-hidden="true" className="phrase-chip__rail">
              <i />
              <i />
            </span>
            <em className="phrase-chip__count">{count}次</em>
          </article>
        );
      })}
    </div>
  );
}

function ModeCard({ title, tone, rows, emptyText }) {
  return (
    <article className={`mode-card mode-card--${tone}`}>
      <div className="mode-card__title">{title}</div>
      <MetaList emptyText={emptyText} rows={rows} />
    </article>
  );
}

function SignalPill({ children, tone = "ink" }) {
  return <span className={`signal-pill signal-pill--${tone}`}>{children}</span>;
}

function SignalTitleRow({ title, pill }) {
  return (
    <div className="signal-list__headline">
      <div className="signal-list__title">{title}</div>
      {pill}
    </div>
  );
}

function FocusBoard({ cards, eyebrow, headline, tone, title }) {
  return (
    <article className={`focus-board focus-board--${tone}`}>
      <div className="focus-board__eyebrow">{eyebrow}</div>
      <div className="focus-board__head">
        <h2>{title}</h2>
        <p>{headline}</p>
      </div>
      <div className="focus-board__grid">
        {cards.map((item) => (
          <div className="focus-board__card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
          </div>
        ))}
      </div>
    </article>
  );
}

function DeferredBlock({ children, isActiveTab, label, minHeight = 220 }) {
  const ref = useRef(null);
  const hasEnteredViewport = useInView(ref, { margin: "160px 0px", once: true });
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    if (shouldMountDeferredBlock({ hasEnteredViewport, hasMounted, isActiveTab })) {
      setHasMounted(true);
    }
  }, [hasEnteredViewport, hasMounted, isActiveTab]);

  return (
    <div className="deferred-block" ref={ref} style={{ minHeight }}>
      {hasMounted ? (
        children
      ) : (
        <div aria-label={`${label} 延迟加载占位`} className="deferred-block__placeholder" role="status">
          <strong>{label}</strong>
          <p>滚动到这里时再挂载，先把首屏切换和筛选压力压下去。</p>
        </div>
      )}
    </div>
  );
}

function RelationshipMap({ chatRows, contactRows, overview, social }) {
  const groups = (chatRows || []).filter((row) => row.chat_type === "group").slice(0, 5);
  const contacts = (contactRows || []).slice(0, 5);
  const [lockedNode, setLockedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  if (!groups.length && !contacts.length) {
    return <div className="empty-state">暂无社交关系图数据</div>;
  }

  const width = 860;
  const height = 520;
  const cx = 430;
  const cy = 250;
  const groupRadius = 190;
  const contactRadius = 224;
  const groupMax = Math.max(...groups.map((row) => Number(row.total_messages || 1)), 1);
  const contactMax = Math.max(...contacts.map((row) => Number(row.total_messages || 1)), 1);

  const defaultState = {
    eyebrow: "Inspector",
    title: "将鼠标移到节点上",
    subtitle: `${overview.mbti_type || "未知"} / ${emotionLabel(overview.dominant_emotion)}`,
    summary: `${formatNumber(overview.total_messages || 0)} 条消息 · ${social.median_response_latency_minutes ?? "--"} 分钟响应`,
    type: "会话中心",
    messages: formatNumber(overview.total_messages || 0),
    business: formatNumber(overview.business_contact_count || 0),
    support: formatNumber(social.private_message_count || 0),
    activeDays: formatNumber(overview.date_span_days || 0),
    selfRatio: "总览视角",
    theme: "center",
  };

  const makeNodeState = (row, theme, kindLabel, subtitle, summary) => ({
    eyebrow: theme === "group" ? "Group Node" : "Contact Node",
    title: row.chat_name || row.contact_name || "未知节点",
    subtitle,
    summary,
    type: kindLabel,
    messages: formatNumber(row.total_messages || 0),
    business: formatNumber(row.business_signal_count || 0),
    support: formatNumber(row.support_signal_count || 0),
    activeDays: formatNumber(row.active_days || 0),
    selfRatio: formatPercent(row.self_ratio || 0),
    theme,
  });

  const groupAngles = spreadAngles(-146, -34, groups.length);
  const contactAngles = spreadAngles(146, 34, contacts.length);

  const groupNodes = groups.map((row, index) => {
    const ratio = Number(row.total_messages || 1) / groupMax;
    const point = polarPoint(cx, cy, groupRadius, groupAngles[index]);
    return {
      key: row.chat_id || row.chat_name || `group-${index}`,
      left: point.x - (144 + ratio * 28) / 2,
      top: point.y - (74 + ratio * 12) / 2,
      width: 144 + ratio * 28,
      height: 74 + ratio * 12,
      lineWidth: 2.4 + ratio * 6.2,
      lineX: point.x,
      lineY: point.y,
      delay: groupAngles[index] / 36,
      row,
      state: makeNodeState(
        row,
        "group",
        "高频群聊",
        `${formatNumber(row.total_messages || 0)} 条消息 · 群聊场`,
        `活跃 ${formatNumber(row.active_days || 0)} 天 · 平均 ${formatNumber(row.avg_message_length || 0, 2)} 字 · 最近 ${row.last_active_at || "未知"}`
      ),
    };
  });

  const contactNodes = contacts.map((row, index) => {
    const ratio = Number(row.total_messages || 1) / contactMax;
    const point = polarPoint(cx, cy, contactRadius, contactAngles[index]);
    return {
      key: row.contact_id || row.contact_name || `contact-${index}`,
      left: point.x - (132 + ratio * 26) / 2,
      top: point.y - (70 + ratio * 10) / 2,
      width: 132 + ratio * 26,
      height: 70 + ratio * 10,
      lineWidth: 2.0 + ratio * 5.4,
      lineX: point.x,
      lineY: point.y,
      delay: contactAngles[index] / 42,
      row,
      state: makeNodeState(
        row,
        "contact",
        "高频私聊",
        `${formatNumber(row.total_messages || 0)} 条私聊 · 一对一关系`,
        `活跃 ${formatNumber(row.active_days || 0)} 天 · 问题占比 ${formatPercent(row.question_ratio || 0)} · 自发 ${formatPercent(row.self_ratio || 0)}`
      ),
    };
  });

  const activeState = hoveredNode || lockedNode || defaultState;

  return (
    <div className="relationship-map">
      <div className="relationship-map__ring relationship-map__ring--outer" />
      <div className="relationship-map__ring relationship-map__ring--inner" />
      <div className="relationship-map__label relationship-map__label--top">高频群聊场</div>
      <div className="relationship-map__label relationship-map__label--bottom">高频私聊场</div>
      <svg className="relationship-map__svg" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
        {groupNodes.map((node) => (
          <line
            className="relationship-map__line relationship-map__line--group"
            key={`line-${node.key}`}
            style={{ strokeWidth: `${node.lineWidth}px` }}
            x1={cx}
            x2={node.lineX}
            y1={cy}
            y2={node.lineY}
          />
        ))}
        {contactNodes.map((node) => (
          <line
            className="relationship-map__line relationship-map__line--contact"
            key={`line-${node.key}`}
            style={{ strokeWidth: `${node.lineWidth}px` }}
            x1={cx}
            x2={node.lineX}
            y1={cy}
            y2={node.lineY}
          />
        ))}
        <circle className="relationship-map__pulse" cx={cx} cy={cy} r="82" />
      </svg>

      <button
        className={`relationship-node relationship-node--center ${!lockedNode && !hoveredNode ? "is-active" : ""}`}
        onClick={() => setLockedNode(null)}
        onFocus={() => setHoveredNode(defaultState)}
        onBlur={() => setHoveredNode(null)}
        onMouseEnter={() => setHoveredNode(defaultState)}
        onMouseLeave={() => setHoveredNode(null)}
        style={{ left: cx - 105, top: cy - 73, width: 210, height: 146 }}
        type="button"
      >
        <div className="relationship-node__eyebrow">Self Core</div>
        <div className="relationship-node__self">你</div>
        <div className="relationship-node__meta">
          {(overview.mbti_type || "未知")} / {emotionLabel(overview.dominant_emotion)}
        </div>
        <div className="relationship-node__summary">
          {formatNumber(overview.total_messages || 0)} 条消息 · {social.median_response_latency_minutes ?? "--"} 分钟响应
        </div>
      </button>

      {groupNodes.map((node) => (
        <button
          className={`relationship-node relationship-node--group ${lockedNode?.title === node.state.title ? "is-active" : ""}`}
          key={node.key}
          onBlur={() => setHoveredNode(null)}
          onClick={() => setLockedNode(node.state)}
          onFocus={() => setHoveredNode(node.state)}
          onMouseEnter={() => setHoveredNode(node.state)}
          onMouseLeave={() => setHoveredNode(null)}
          style={{
            left: node.left,
            top: node.top,
            width: node.width,
            height: node.height,
            animationDelay: `${node.delay}s`,
          }}
          type="button"
        >
          <div className="relationship-node__title">{clipText(node.row.chat_name, 18)}</div>
          <div className="relationship-node__meta">{formatNumber(node.row.total_messages)} 条消息</div>
          <div className="relationship-node__badges">
            {Number(node.row.business_signal_count) ? (
              <span className="relationship-node__badge relationship-node__badge--sea">商业 {node.row.business_signal_count}</span>
            ) : null}
            {Number(node.row.support_signal_count) ? (
              <span className="relationship-node__badge relationship-node__badge--gold">售后 {node.row.support_signal_count}</span>
            ) : null}
          </div>
        </button>
      ))}

      {contactNodes.map((node) => (
        <button
          className={`relationship-node relationship-node--contact ${lockedNode?.title === node.state.title ? "is-active" : ""}`}
          key={node.key}
          onBlur={() => setHoveredNode(null)}
          onClick={() => setLockedNode(node.state)}
          onFocus={() => setHoveredNode(node.state)}
          onMouseEnter={() => setHoveredNode(node.state)}
          onMouseLeave={() => setHoveredNode(null)}
          style={{
            left: node.left,
            top: node.top,
            width: node.width,
            height: node.height,
            animationDelay: `${node.delay}s`,
          }}
          type="button"
        >
          <div className="relationship-node__title">{clipText(node.row.contact_name, 16)}</div>
          <div className="relationship-node__meta">{formatNumber(node.row.total_messages)} 条私聊</div>
          <div className="relationship-node__badges">
            {Number(node.row.business_signal_count) ? (
              <span className="relationship-node__badge relationship-node__badge--sea">商业 {node.row.business_signal_count}</span>
            ) : null}
            {Number(node.row.support_signal_count) ? (
              <span className="relationship-node__badge relationship-node__badge--gold">售后 {node.row.support_signal_count}</span>
            ) : null}
          </div>
        </button>
      ))}

      <aside className={`relationship-inspector relationship-inspector--${activeState.theme}`}>
        <div className="relationship-inspector__eyebrow">{activeState.eyebrow}</div>
        <h3 className="relationship-inspector__title">{activeState.title}</h3>
        <div className="relationship-inspector__subtitle">{activeState.subtitle}</div>
        <p className="relationship-inspector__summary">{activeState.summary}</p>
        <div className="relationship-inspector__grid">
          <div className="relationship-inspector__metric">
            <span>节点类型</span>
            <strong>{activeState.type}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>消息量</span>
            <strong>{activeState.messages}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>商业</span>
            <strong>{activeState.business}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>售后/私聊</span>
            <strong>{activeState.support}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>活跃天数</span>
            <strong>{activeState.activeDays}</strong>
          </div>
          <div className="relationship-inspector__metric">
            <span>自发占比</span>
            <strong>{activeState.selfRatio}</strong>
          </div>
        </div>
        <button className="relationship-inspector__reset" onClick={() => setLockedNode(null)} type="button">
          重置到中心
        </button>
      </aside>
    </div>
  );
}

export {
  BarList,
  BulletList,
  DeferredBlock,
  DimensionMatrix,
  EmotionDonut,
  FocusBoard,
  MetaList,
  ModeCard,
  PhraseCloud,
  RelationshipMap,
  SectionKicker,
  SignalList,
  SignalPill,
  SignalTitleRow,
  StoryDeck,
  SummaryGrid,
  TrendChart,
  emotionTone,
};

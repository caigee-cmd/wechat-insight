import { useInView } from "motion/react";
import { useEffect, useRef, useState } from "react";

import RelationshipMap from "./RelationshipSphere";

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
  { accent: "sea", lane: "mid", x: 14, y: 33, width: 27, mobileSpan: 2, driftX: -10, driftY: -6, rotate: -1.8 },
  { accent: "ink", lane: "mid", x: 60, y: 29, width: 24, mobileSpan: 2, driftX: 8, driftY: 2, rotate: 1.4 },
  { accent: "gold", lane: "top", x: 26, y: 6, width: 21, mobileSpan: 1, driftX: -5, driftY: 5, rotate: -0.9 },
  { accent: "sea", lane: "bottom", x: 55, y: 63, width: 27, mobileSpan: 2, driftX: 6, driftY: -5, rotate: 1.1 },
  { accent: "ink", lane: "mid", x: 2, y: 59, width: 21, mobileSpan: 1, driftX: -8, driftY: 4, rotate: -1.2 },
  { accent: "gold", lane: "top", x: 76, y: 8, width: 17, mobileSpan: 1, driftX: 5, driftY: -4, rotate: 1.2 },
  { accent: "sea", lane: "bottom", x: 34, y: 76, width: 18, mobileSpan: 1, driftX: -4, driftY: 6, rotate: -0.7 },
  { accent: "ink", lane: "top", x: 43, y: 0, width: 18, mobileSpan: 1, driftX: 7, driftY: -3, rotate: 0.8 },
  { accent: "gold", lane: "mid", x: 81, y: 48, width: 15, mobileSpan: 1, driftX: 6, driftY: 5, rotate: -0.6 },
  { accent: "sea", lane: "top", x: 7, y: 13, width: 15, mobileSpan: 1, driftX: -3, driftY: 4, rotate: 0.9 },
  { accent: "ink", lane: "mid", x: 23, y: 56, width: 17, mobileSpan: 1, driftX: 4, driftY: -5, rotate: 0.5 },
  { accent: "gold", lane: "bottom", x: 63, y: 80, width: 17, mobileSpan: 1, driftX: -5, driftY: 4, rotate: -0.8 },
];

const PHRASE_ACCENTS = ["sea", "ink", "gold"];

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

function resolvePhraseAccentSeed(text) {
  const source = String(text || "").trim();
  if (!source) {
    return PHRASE_ACCENTS[0];
  }
  let hash = 0;
  for (const char of source) {
    hash = (hash + char.codePointAt(0)) % PHRASE_ACCENTS.length;
  }
  return PHRASE_ACCENTS[hash];
}

function buildPhraseFocusSummary({ count, isTop, topCount, totalCount }) {
  const share = totalCount > 0 ? formatPercent(count / totalCount) : "--";
  if (isTop) {
    return "当前高频池里最突出的表达";
  }
  if (count === topCount) {
    return `与最高频并列，占当前高频池 ${share}`;
  }
  return `比最高频少 ${topCount - count} 次，占当前高频池 ${share}`;
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
  const topPhrase = rows[0];
  const topCount = Number(topPhrase?.count || 0);
  const totalCount = rows.reduce((sum, item) => sum + Number(item?.count || 0), 0);
  const phraseRows = rows.map((item, index) => {
    const count = Number(item.count || 1);
    const accent = resolvePhraseAccentSeed(item.text);
    const preset = PHRASE_FLOW_LAYOUT_PRESETS[index % PHRASE_FLOW_LAYOUT_PRESETS.length];
    return {
      ...item,
      accent,
      count,
      isTop: index === 0,
      key: `${item.text}-${item.count}`,
      lane: preset.lane,
      preset,
      summary: buildPhraseFocusSummary({
        count,
        isTop: index === 0,
        topCount,
        totalCount,
      }),
    };
  });
  const [activePhraseKey, setActivePhraseKey] = useState(null);
  const activePhrase = phraseRows.find((item) => item.key === activePhraseKey) || phraseRows[0];
  const coreEyebrow = activePhrase.isTop ? "Top Phrase" : "Phrase Focus";

  return (
    <div
      aria-label="口癖排版云"
      className={`phrase-cloud phrase-cloud--lane-${activePhrase.lane} phrase-cloud--tone-${activePhrase.accent}`}
    >
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
      <div className={`phrase-cloud__core phrase-cloud__core--${activePhrase.accent}`}>
        <span>{coreEyebrow}</span>
        <strong>{activePhrase.text}</strong>
        <b>{activePhrase.count}次</b>
        <small>{activePhrase.summary}</small>
      </div>
      {phraseRows.map((item, index) => {
        const normalized = item.count / maxCount;
        const size = 0.98 + normalized * 0.9;
        const weight = 540 + Math.round(normalized * 180);
        return (
          <article
            className={`phrase-chip phrase-chip--${item.accent} ${activePhrase.key === item.key ? "phrase-chip--active" : ""}`}
            key={item.key}
            onBlur={() => setActivePhraseKey(null)}
            onFocus={() => setActivePhraseKey(item.key)}
            onMouseEnter={() => setActivePhraseKey(item.key)}
            onMouseLeave={() => setActivePhraseKey(null)}
            tabIndex={0}
            style={{
              "--x": `${item.preset.x}%`,
              "--y": `${item.preset.y}%`,
              "--width": `${item.preset.width}%`,
              "--span-mobile": item.preset.mobileSpan,
              "--drift-x": `${item.preset.driftX}px`,
              "--drift-y": `${item.preset.driftY}px`,
              "--rotate": `${item.preset.rotate}deg`,
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
            <em className="phrase-chip__count">{item.count}次</em>
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

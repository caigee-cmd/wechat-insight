import { Suspense, lazy, memo, startTransition, useDeferredValue, useEffect, useState } from "react";
import {
  buildHeroRows,
  buildMetricCards,
  buildOrbitRows,
} from "./lib/dashboardChrome";
import {
  buildActiveTabData,
  shouldRenderRelationshipMap,
} from "./lib/dashboardTabState";
import { buildDashboardViewState } from "./lib/dashboardViewState";
import {
  getNearbySectionIds,
  preloadDashboardSection,
  SECTION_LOADERS,
  resolveDashboardSectionId,
} from "./lib/dashboardSectionRegistry";
import {
  buildPersonaSnapshot,
  buildSignalsSnapshot,
} from "./lib/insightSummary";
import {
  formatDisplayDateTime,
  formatRoleLabel,
  readInitialUiState,
  writeUiStateQuery,
} from "./lib/presentation";
import Aurora from "./components/reactbits/Aurora";
import BorderGlow from "./components/reactbits/BorderGlow";
import CountUp from "./components/reactbits/CountUp";
import ShinyText from "./components/reactbits/ShinyText";
import SpotlightCard from "./components/reactbits/SpotlightCard";

const TABS = [
  { id: "overview", label: "总览", eyebrow: "Pulse", number: "01" },
  { id: "activity", label: "活跃分布", eyebrow: "Orbit", number: "02" },
  { id: "signals", label: "信号洞察", eyebrow: "Leads", number: "03" },
  { id: "persona", label: "高级分析", eyebrow: "Persona", number: "04" },
  { id: "artifacts", label: "产物文件", eyebrow: "Files", number: "05" },
];

const WINDOW_OPTIONS = [
  { id: "all", label: "全部", days: null },
  { id: "7d", label: "近 7 天", days: 7 },
  { id: "30d", label: "近 30 天", days: 30 },
];

const LAZY_SECTIONS = {
  overview: lazy(SECTION_LOADERS.overview),
  activity: lazy(SECTION_LOADERS.activity),
  signals: lazy(SECTION_LOADERS.signals),
  persona: lazy(SECTION_LOADERS.persona),
  artifacts: lazy(SECTION_LOADERS.artifacts),
};

function normalizeQuery(value) {
  return (value || "").trim().toLowerCase();
}

function includesQuery(parts, query) {
  if (!query) {
    return true;
  }
  return parts.some((part) => String(part || "").toLowerCase().includes(query));
}

function filterPairs(items, query) {
  return (items || []).filter(([name, value]) => includesQuery([name, value], query));
}

function filterSignals(items, query, getParts) {
  return (items || []).filter((item) => includesQuery(getParts(item), query));
}

function formatPairLabel(hour, count) {
  return [`${hour}时`, count];
}

function sumBy(rows, key) {
  return (rows || []).reduce((total, row) => total + (Number(row?.[key]) || 0), 0);
}

function getWindowRows(rows, windowId) {
  const option = WINDOW_OPTIONS.find((item) => item.id === windowId) || WINDOW_OPTIONS[0];
  if (!option.days) {
    return rows || [];
  }
  return (rows || []).slice(-option.days);
}

function getWindowLabel(windowId) {
  return (WINDOW_OPTIONS.find((item) => item.id === windowId) || WINDOW_OPTIONS[0]).label;
}

function getPeakDay(rows) {
  if (!rows.length) {
    return null;
  }
  return rows.reduce((best, row) => {
    if (!best) {
      return row;
    }
    return (Number(row.total_messages) || 0) > (Number(best.total_messages) || 0) ? row : best;
  }, null);
}

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

function parseDisplayNumber(value) {
  const number = Number(String(value ?? "").replace(/,/g, ""));
  return Number.isFinite(number) ? number : null;
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

function MetricCard({ label, value, tone, detail }) {
  const numericValue = parseDisplayNumber(value);

  return (
    <SpotlightCard
      className={`metric-card metric-card--${tone}`}
      spotlightColor="rgba(23, 224, 177, 0.16)"
    >
      <div className="metric-card__label">{label}</div>
      <div className="metric-card__value">
        {numericValue === null ? (
          formatNumber(value)
        ) : (
          <CountUp to={numericValue} duration={1.25} separator="," />
        )}
      </div>
      <div className="metric-card__detail">{detail}</div>
    </SpotlightCard>
  );
}

const MetricsStrip = memo(function MetricsStrip({
  activeChatCount,
  businessContactCount,
  pendingFollowupCount,
  textMessages,
  totalMessages,
  totalPrivateContacts,
}) {
  const cards = buildMetricCards({
    active_chat_count: activeChatCount,
    business_contact_count: businessContactCount,
    pending_followup_count: pendingFollowupCount,
    text_messages: textMessages,
    total_messages: totalMessages,
    total_private_contacts: totalPrivateContacts,
  });

  return (
    <section className="metrics-grid">
      {cards.map((item) => (
        <MetricCard detail={item.detail} key={item.label} label={item.label} tone={item.tone} value={item.value} />
      ))}
    </section>
  );
});

function DockIconGlyph({ children }) {
  return <span className="dock-glyph">{children}</span>;
}

function OverviewGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3.5" y="4" width="7" height="7" rx="2" />
      <rect x="13.5" y="4" width="7" height="5" rx="2" />
      <rect x="3.5" y="13" width="7" height="7" rx="2" />
      <rect x="13.5" y="11" width="7" height="9" rx="2" />
    </svg>
  );
}

function ActivityGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 16c2.2-5 4.2-7.5 6-7.5S13.5 15 15.6 15c1.5 0 2.9-2 4.4-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="4" cy="16" r="1.5" />
      <circle cx="10" cy="8.5" r="1.5" />
      <circle cx="15.6" cy="15" r="1.5" />
      <circle cx="20" cy="9" r="1.5" />
    </svg>
  );
}

function SignalsGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 18.5V13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M12 18.5V7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M19 18.5V10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="5" cy="11" r="2" />
      <circle cx="12" cy="5" r="2" />
      <circle cx="19" cy="8" r="2" />
    </svg>
  );
}

function PersonaGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 4c4.2 0 7.5 3.1 7.5 7 0 3.2-2.3 5.9-5.5 6.7L12 20l-2-2.3C6.8 16.9 4.5 14.2 4.5 11c0-3.9 3.3-7 7.5-7Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <circle cx="9.2" cy="10.2" r="1" />
      <circle cx="14.8" cy="10.2" r="1" />
      <path d="M9 13.4c1 .8 2 .8 3 .8s2 0 3-.8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function FilesGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 5.5A2.5 2.5 0 0 1 8.5 3h4.3L18 8.2V18.5A2.5 2.5 0 0 1 15.5 21h-7A2.5 2.5 0 0 1 6 18.5Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M12.8 3v5.2H18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M9 13h6M9 16.5h6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
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

const DashboardHero = memo(
  function DashboardHero({
    avgMessageLength,
    businessContactCount,
    dominantEmotionLabel,
    dominantEmotionTone,
    generatedAtText,
    groupMessageCount,
    medianResponseText,
    mbtiType,
    onReload,
    overviewDays,
    pendingFollowupCount,
    privateMessageCount,
    schemaVersion,
    totalMessages,
  }) {
    const heroRows = buildHeroRows({
      emotionLabel: dominantEmotionLabel,
      emotionTone: dominantEmotionTone,
      mbtiType,
      overviewDays,
    });
    const orbitRows = buildOrbitRows({
      avgMessageLength,
      groupMessageCount,
      medianResponseText,
      privateMessageCount,
    });

    return (
      <section className="hero hero--workbench">
        <div className="hero__masthead">
          <div className="hero__identity">
            <div className="hero__eyebrow">WeChat Insight</div>
            <h1>
              微信洞察{" "}
              <ShinyText
                className="gradient-text hero-shiny"
                color="#d66a35"
                shineColor="#fff0b8"
                speed={3.4}
                text="关系工作台"
              />
            </h1>
          </div>
          <div className="hero__meta-panel" aria-label="Dashboard metadata">
            <div>
              <span>Schema</span>
              <strong>{schemaVersion || "未加载"}</strong>
            </div>
            <div>
              <span>生成时间</span>
              <strong>{generatedAtText}</strong>
            </div>
            <div>
              <span>覆盖天数</span>
              <strong>{overviewDays}</strong>
            </div>
            <button className="hero__reload" onClick={onReload} type="button">
              刷新数据
            </button>
          </div>
        </div>

        <div className="hero__matrix">
          <BorderGlow
            animated
            backgroundColor="#fff4df"
            borderRadius={24}
            className="hero-glow-shell"
            colors={["#ff9f5a", "#f5c84f", "#6dbf91"]}
            fillOpacity={0.22}
            glowColor="32 93 66"
            glowIntensity={0.54}
            glowRadius={18}
          >
            <article className="hero__primary-metric">
              <span>Conversation Pulse</span>
              <strong>
                <CountUp to={parseDisplayNumber(totalMessages) || 0} duration={1.6} separator="," />
              </strong>
              <p>把聊天量、关系密度和待推进信号压到同一个决策视图。</p>
            </article>
          </BorderGlow>

          <div className="hero-chip-row">
            {heroRows.map(([label, value, tone]) => (
              <SpotlightCard
                className={`hero-chip hero-chip--${tone}`}
                key={label}
                spotlightColor="rgba(246, 180, 77, 0.18)"
              >
                <span>{label}</span>
                <strong>{value}</strong>
              </SpotlightCard>
            ))}
          </div>

          <article className="hero-orbit hero-orbit--steady">
            <div className="hero-orbit__eyebrow">Message Orbit</div>
            <div className="hero-orbit__spark">
              <MetaList emptyText="暂无摘要指标" rows={orbitRows} />
            </div>
          </article>

          <div className="hero-orbit__grid" aria-label="Key signal summary">
            <SpotlightCard className="orbit-chip" spotlightColor="rgba(23, 224, 177, 0.14)">
              <span>主导情绪</span>
              <strong>{dominantEmotionLabel}</strong>
            </SpotlightCard>
            <SpotlightCard className="orbit-chip" spotlightColor="rgba(142, 162, 255, 0.16)">
              <span>人格推测</span>
              <strong>{mbtiType}</strong>
            </SpotlightCard>
            <SpotlightCard className="orbit-chip" spotlightColor="rgba(246, 180, 77, 0.16)">
              <span>商机联系人</span>
              <strong>{businessContactCount}</strong>
            </SpotlightCard>
            <SpotlightCard className="orbit-chip" spotlightColor="rgba(255, 107, 107, 0.14)">
              <span>待跟进</span>
              <strong>{pendingFollowupCount}</strong>
            </SpotlightCard>
          </div>
        </div>
      </section>
    );
  },
  (prev, next) =>
    prev.avgMessageLength === next.avgMessageLength &&
    prev.businessContactCount === next.businessContactCount &&
    prev.dominantEmotionLabel === next.dominantEmotionLabel &&
    prev.dominantEmotionTone === next.dominantEmotionTone &&
    prev.generatedAtText === next.generatedAtText &&
    prev.groupMessageCount === next.groupMessageCount &&
    prev.medianResponseText === next.medianResponseText &&
    prev.mbtiType === next.mbtiType &&
    prev.overviewDays === next.overviewDays &&
    prev.pendingFollowupCount === next.pendingFollowupCount &&
    prev.privateMessageCount === next.privateMessageCount &&
    prev.schemaVersion === next.schemaVersion &&
    prev.totalMessages === next.totalMessages
);

function App() {
  const initialUiState = readInitialUiState(typeof window !== "undefined" ? window.location.search : "");
  const [payload, setPayload] = useState(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState(initialUiState.activeTab);
  const [isRelationshipMapExpanded, setIsRelationshipMapExpanded] = useState(false);
  const [windowId, setWindowId] = useState(initialUiState.windowId);
  const [query, setQuery] = useState(initialUiState.query);
  const deferredQuery = useDeferredValue(normalizeQuery(query));
  const viewState = buildDashboardViewState(query);

  useEffect(() => {
    let cancelled = false;

    async function loadPayload() {
      setStatus("loading");
      setError("");
      try {
        const response = await fetch(`/report_payload.json?t=${Date.now()}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const nextPayload = await response.json();
        if (!cancelled) {
          setPayload(nextPayload);
          setStatus("ready");
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError.message || "加载失败");
          setStatus("error");
        }
      }
    }

    loadPayload();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const nextSearch = writeUiStateQuery({
      activeTab,
      baseSearch: window.location.search,
      query,
      windowId,
    });
    const nextUrl = `${window.location.pathname}${nextSearch}${window.location.hash}`;
    window.history.replaceState({}, "", nextUrl);
  }, [activeTab, query, windowId]);

  const overview = payload?.overview || {};
  const sections = payload?.sections || {};
  const daily = sections.daily || {};
  const customer = sections.customer || {};
  const labels = sections.labels || {};
  const features = sections.features || {};
  const emotion = sections.emotion || {};
  const mbti = sections.mbti || {};
  const speech = sections.speech || {};
  const social = sections.social || {};
  const artifacts = payload?.artifacts || {};
  const sources = payload?.sources || {};

  const dailyActivity = features.daily_activity || [];
  const chatLeaderboard = features.chat_leaderboard || [];
  const contactLeaderboard = features.contact_leaderboard || [];
  const windowRows = getWindowRows(dailyActivity, windowId);
  const windowLabel = getWindowLabel(windowId);
  const peakDay = getPeakDay(windowRows);

  const roleCounts = customer.role_counts || {};
  const roleRows = [
    [formatRoleLabel("customer"), roleCounts.customer || 0],
    [formatRoleLabel("vendor"), roleCounts.vendor || 0],
    [formatRoleLabel("unknown"), roleCounts.unknown || 0],
  ];
  const topGroupRow = chatLeaderboard.find((item) => item.chat_type === "group");
  const topContactRow = contactLeaderboard[0];
  const busiestBusinessChat = chatLeaderboard.reduce(
    (best, row) =>
      Number(row.business_signal_count || 0) > Number(best?.business_signal_count || 0) ? row : best,
    null
  );
  const busiestSupportChat = chatLeaderboard.reduce(
    (best, row) =>
      Number(row.support_signal_count || 0) > Number(best?.support_signal_count || 0) ? row : best,
    null
  );
  const dominantEmotionLabel = emotionLabel(overview.dominant_emotion || emotion.dominant_emotion);
  const dominantEmotionTone = emotionTone(overview.dominant_emotion || emotion.dominant_emotion);
  const generatedAtText = formatDisplayDateTime(payload?.generated_at);
  const medianResponseText =
    social.median_response_latency_minutes === undefined || social.median_response_latency_minutes === null
      ? "--"
      : `${formatNumber(social.median_response_latency_minutes, 2)} 分钟`;
  const mbtiType = overview.mbti_type || mbti.mbti_type || "--";
  const overviewDays = formatNumber(overview.date_span_days || 0);
  const avgMessageLength = formatNumber(overview.avg_message_length || speech.avg_message_length || 0, 2);
  const businessContactCount = formatNumber(overview.business_contact_count || 0);
  const groupMessageCount = formatNumber(overview.group_message_count || 0);
  const labelMetaRows = [
    ["标签联系人", labels.generated_contacts],
    ["私聊联系人", labels.total_private_contacts],
    ["自动建议", labels.applied_suggestions],
  ];
  const lifeModeToneValue = emotion.persona_modes?.life?.dominant_emotion;
  const pendingFollowupCount = formatNumber(overview.pending_followup_count || 0);
  const phraseItems = speech.top_terms || speech.repeated_phrases || [];
  const privateMessageCount = formatNumber(overview.private_message_count || 0);
  const totalMessages = formatNumber(overview.total_messages || 0);
  const workModeToneValue = emotion.persona_modes?.work?.dominant_emotion;
  const tabData = buildActiveTabData(activeTab, {
    overview: () => ({
      summaryLines: (daily.summary_lines || []).filter((line) => includesQuery([line], deferredQuery)),
      windowSummaryRows: [
        ["窗口消息", sumBy(windowRows, "total_messages"), "ink"],
        ["商业信号", sumBy(windowRows, "business_signal_count"), "sea"],
        ["待办信号", sumBy(windowRows, "action_signal_count"), "gold"],
        ["售后信号", sumBy(windowRows, "support_signal_count"), "ink"],
      ],
    }),
    activity: () => ({
      filteredDailyRows: filterSignals(
        windowRows,
        deferredQuery,
        (item) => [item.date, item.total_messages, item.business_signal_count, item.support_signal_count]
      ),
      relationshipRows: [
        ["最强群聊", topGroupRow?.chat_name],
        ["最强私聊", topContactRow?.contact_name],
        ["熬夜占比", formatPercent(social.night_message_ratio || 0)],
        [
          "中位响应",
          social.median_response_latency_minutes === undefined || social.median_response_latency_minutes === null
            ? ""
            : `${social.median_response_latency_minutes} 分钟`,
        ],
        ["商业密度群", busiestBusinessChat?.chat_name],
        ["售后压力群", busiestSupportChat?.chat_name],
      ].filter(([label, value]) => includesQuery([label, value], deferredQuery)),
      topChats: filterPairs(
        (chatLeaderboard.length
          ? chatLeaderboard.map((item) => [item.chat_name, item.total_messages])
          : daily.top_chats || []),
        deferredQuery
      ),
      topContacts: filterPairs(
        (contactLeaderboard.length
          ? contactLeaderboard.map((item) => [item.contact_name, item.total_messages])
          : daily.top_contacts || []),
        deferredQuery
      ),
      topHours: filterPairs(
        (daily.top_hours || []).map(([hour, count]) => formatPairLabel(hour, count)),
        deferredQuery
      ),
    }),
    artifacts: () => ({
      artifactRows: [
        ["Payload", artifacts.payload_path],
        ["日报", artifacts.daily_report_path],
        ["客户报告", artifacts.customer_report_path],
        ["情绪报告", artifacts.emotion_report_path],
        ["MBTI 报告", artifacts.mbti_report_path],
        ["口癖报告", artifacts.speech_report_path],
        ["社交图谱", artifacts.social_report_path],
        ["标签文件", artifacts.labels_path],
        ["enriched", artifacts.feature_files?.messages_enriched],
        ["daily_features", artifacts.feature_files?.daily_features],
        ["chat_features", artifacts.feature_files?.chat_features],
        ["contact_features", artifacts.feature_files?.contact_features],
        ["输入文件", (sources.input_files || []).join(", ")],
        ["特征目录", features.output_dir],
      ].filter(([label, value]) => includesQuery([label, value], deferredQuery)),
    }),
    persona: () => {
      const topEmotionalChats = filterSignals(
        emotion.top_emotional_chats || [],
        deferredQuery,
        (item) => [item.chat_name, item.emotion_score, item.positive, item.negative, item.angry]
      );

      return {
        lifeModeRows: [
          ["MBTI", mbti.persona_modes?.life?.mbti_type],
          ["情绪", emotionLabel(emotion.persona_modes?.life?.dominant_emotion)],
          ["口癖", speech.persona_modes?.life?.repeated_phrases?.[0]?.text],
          ["高频会话", social.persona_modes?.life?.top_chats?.[0]?.[0]],
        ].filter(([label, value]) => includesQuery([label, value], deferredQuery)),
        personaSnapshot: buildPersonaSnapshot({
          overview,
          social,
          speech,
          topEmotionalChats,
        }),
        socialMetaRows: [
          [
            "中位响应时延",
            social.median_response_latency_minutes === undefined || social.median_response_latency_minutes === null
              ? ""
              : `${social.median_response_latency_minutes} 分钟`,
          ],
          ["群聊消息", social.group_message_count],
          ["私聊消息", social.private_message_count],
          ["夜间占比", social.night_message_ratio === undefined ? "" : `${((social.night_message_ratio || 0) * 100).toFixed(1)}%`],
        ].filter(([label, value]) => includesQuery([label, value], deferredQuery)),
        socialTopChats: filterPairs(social.top_chats || [], deferredQuery),
        topEmotionalChats,
        workModeRows: [
          ["MBTI", mbti.persona_modes?.work?.mbti_type],
          ["情绪", emotionLabel(emotion.persona_modes?.work?.dominant_emotion)],
          ["口癖", speech.persona_modes?.work?.repeated_phrases?.[0]?.text],
          ["高频会话", social.persona_modes?.work?.top_chats?.[0]?.[0]],
        ].filter(([label, value]) => includesQuery([label, value], deferredQuery)),
      };
    },
    signals: () => {
      const dailyFollowups = filterSignals(
        daily.pending_followups || [],
        deferredQuery,
        (item) => [item.chat_name, item.content, ...(item.labels || [])]
      );
      const topOpportunities = filterSignals(
        customer.top_opportunities || [],
        deferredQuery,
        (item) => [item.contact_name, item.role, item.stage]
      );
      const topRisks = filterSignals(
        customer.top_support_risks || [],
        deferredQuery,
        (item) => [item.contact_name, item.role, item.stage]
      );
      const customerFollowups = filterSignals(
        customer.pending_followups || [],
        deferredQuery,
        (item) => [
          item.contact_name,
          item.pending_followup?.content,
          ...(item.pending_followup?.labels || []),
        ]
      );

      return {
        customerFollowups,
        dailyFollowups,
        signalsSnapshot: buildSignalsSnapshot({
          customerFollowups,
          dailyFollowups,
          topOpportunities,
          topRisks,
        }),
        topOpportunities,
        topRisks,
      };
    },
  });
  const {
    artifactRows = [],
    customerFollowups = [],
    dailyFollowups = [],
    filteredDailyRows = [],
    lifeModeRows = [],
    personaSnapshot = { cards: [], headline: "" },
    relationshipRows = [],
    signalsSnapshot = { cards: [], headline: "" },
    socialMetaRows = [],
    socialTopChats = [],
    summaryLines = [],
    topChats = [],
    topContacts = [],
    topEmotionalChats = [],
    topHours = [],
    topOpportunities = [],
    topRisks = [],
    windowSummaryRows = [],
    workModeRows = [],
  } = tabData;
  const showRelationshipMap = shouldRenderRelationshipMap({
    activeTab,
    isExpanded: isRelationshipMapExpanded,
    isFiltering: viewState.isFiltering,
  });
  const activeSectionId = resolveDashboardSectionId(activeTab);
  const ActiveSection = LAZY_SECTIONS[activeSectionId];

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const warmupSectionIds = [activeSectionId, ...getNearbySectionIds(activeSectionId)];
    const warmup = () => {
      warmupSectionIds.forEach((sectionId) => {
        preloadDashboardSection(sectionId);
      });
    };

    if (typeof window.requestIdleCallback === "function") {
      const idleId = window.requestIdleCallback(warmup, { timeout: 400 });
      return () => window.cancelIdleCallback(idleId);
    }

    const timerId = window.setTimeout(warmup, 120);
    return () => window.clearTimeout(timerId);
  }, [activeSectionId]);

  const sectionPropsById = {
    overview: {
      labelMetaRows,
      peakDay,
      roleRows,
      summaryLines,
      windowLabel,
      windowRows,
      windowSummaryRows,
    },
    activity: {
      chatLeaderboard,
      contactLeaderboard,
      filteredDailyRows,
      isRelationshipMapExpanded,
      onExpandRelationshipMap: () => setIsRelationshipMapExpanded(true),
      overview,
      relationshipRows,
      showRelationshipMap,
      social,
      topChats,
      topContacts,
      topHours,
      viewStateIsFiltering: viewState.isFiltering,
      windowLabel,
    },
    signals: {
      customerFollowups,
      dailyFollowups,
      signalsSnapshot,
      topOpportunities,
      topRisks,
    },
    persona: {
      emotionDistribution: emotion.emotion_distribution,
      lifeModeRows,
      lifeModeToneValue,
      mbtiDimensions: mbti.dimensions,
      personaSnapshot,
      phraseItems,
      socialMetaRows,
      socialTopChats,
      topEmotionalChats,
      workModeRows,
      workModeToneValue,
    },
    artifacts: {
      artifactRows,
    },
  };
  const iconById = {
    overview: <OverviewGlyph />,
    activity: <ActivityGlyph />,
    signals: <SignalsGlyph />,
    persona: <PersonaGlyph />,
    artifacts: <FilesGlyph />,
  };

  function handleTabChange(nextTab) {
    startTransition(() => {
      setActiveTab(nextTab);
    });
  }

  function handleWindowChange(nextWindowId) {
    startTransition(() => {
      setWindowId(nextWindowId);
    });
  }

  async function handleReload() {
    setStatus("loading");
    setError("");
    try {
      const response = await fetch(`/report_payload.json?t=${Date.now()}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const nextPayload = await response.json();
      setPayload(nextPayload);
      setStatus("ready");
    } catch (reloadError) {
      setError(reloadError.message || "刷新失败");
      setStatus("error");
    }
  }

  return (
    <main className={viewState.shellClassName}>
      <div className="page-aurora" aria-hidden="true">
        <Aurora
          amplitude={0.55}
          blend={0.34}
          colorStops={["#ffe2ad", "#ff9f6e", "#8ed2a9"]}
          speed={0.34}
        />
      </div>

      <DashboardHero
        avgMessageLength={avgMessageLength}
        businessContactCount={businessContactCount}
        dominantEmotionLabel={dominantEmotionLabel}
        dominantEmotionTone={dominantEmotionTone}
        generatedAtText={generatedAtText}
        groupMessageCount={groupMessageCount}
        mbtiType={mbtiType}
        medianResponseText={medianResponseText}
        onReload={handleReload}
        overviewDays={overviewDays}
        pendingFollowupCount={pendingFollowupCount}
        privateMessageCount={privateMessageCount}
        schemaVersion={payload?.schema_version || "未加载"}
        totalMessages={totalMessages}
      />

      <section className="toolbar">
        <div className="dock-toolbar">
          <div className="dock-tabs dock-tabs--steady" role="tablist" aria-label="数据视图切换">
            {TABS.map((tab) => (
              <button
                aria-selected={activeTab === tab.id}
                className={`dock-tab ${activeTab === tab.id ? "dock-tab--active" : ""}`}
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                onFocus={() => preloadDashboardSection(tab.id)}
                onMouseEnter={() => preloadDashboardSection(tab.id)}
                role="tab"
                type="button"
              >
                <span className="dock-tab__index">
                  <DockIconGlyph>{iconById[tab.id]}</DockIconGlyph>
                </span>
                <span className="dock-tab__text">
                  <strong>{tab.label}</strong>
                  <small>
                    {tab.number} · {tab.eyebrow}
                  </small>
                </span>
              </button>
            ))}
          </div>
        </div>
        <div className="toolbar__aside">
          <div className="window-switcher">
            {WINDOW_OPTIONS.map((option) => (
              <button
                className={`window-pill ${windowId === option.id ? "window-pill--active" : ""}`}
                key={option.id}
                onClick={() => handleWindowChange(option.id)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
          <label className="search">
            <span>检索</span>
            <input
              aria-label="检索联系人、会话、标签或路径"
              autoComplete="off"
              name="dashboard-search"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="输入联系人、会话、标签、路径…"
              spellCheck={false}
              type="search"
              value={query}
            />
          </label>
        </div>
      </section>

      {status === "loading" ? (
        <section className="panel panel--state">正在加载 dashboard 数据…</section>
      ) : null}
      {status === "error" ? (
        <section className="panel panel--state panel--error">加载失败：{error}</section>
      ) : null}

      {status === "ready" ? (
        <>
          <MetricsStrip
            activeChatCount={overview.active_chat_count || 0}
            businessContactCount={overview.business_contact_count || 0}
            pendingFollowupCount={overview.pending_followup_count || 0}
            textMessages={overview.text_messages || 0}
            totalMessages={overview.total_messages || 0}
            totalPrivateContacts={overview.total_private_contacts || 0}
          />

          <Suspense fallback={<section className="panel panel--state">正在加载当前视图…</section>}>
            <ActiveSection {...sectionPropsById[activeSectionId]} />
          </Suspense>
        </>
      ) : null}
    </main>
  );
}

export default App;

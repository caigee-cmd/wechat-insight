import { formatDisplayDateTime, formatRoleLabel, formatStageLabel } from "../lib/presentation";
import {
  FocusBoard,
  SectionKicker,
  SignalList,
  SignalPill,
  SignalTitleRow,
} from "../components/dashboardPrimitives";

export default function SignalsSection({
  customerFollowups,
  dailyFollowups,
  signalsSnapshot,
  topOpportunities,
  topRisks,
}) {
  return (
    <>
      <SectionKicker title="Signals" subtitle="哪些人、哪些话，最值得你继续跟进" />
      <FocusBoard
        cards={signalsSnapshot.cards}
        eyebrow="Action Board"
        headline={signalsSnapshot.headline}
        title="先看这 4 个信号"
        tone="gold"
      />
      <section className="content-grid">
        <article className="panel">
          <h2>待跟进信号</h2>
          <p className="panel__subtle">别人已经把球抛过来，但你还没真正接住的聊天节点。</p>
          <SignalList
            emptyText="暂无待跟进会话"
            items={dailyFollowups}
            renderBody={(item) => (
              <li className="signal-list__item" key={`${item.chat_name}-${item.datetime}`}>
                <SignalTitleRow
                  title={item.chat_name}
                  pill={<SignalPill tone="sea">{(item.labels || [])[0] || "待跟进"}</SignalPill>}
                />
                <div className="signal-list__body">{item.content}</div>
                <div className="signal-list__meta">
                  {(item.labels || []).join(" / ")} · {formatDisplayDateTime(item.datetime)}
                </div>
              </li>
            )}
          />
        </article>
        <article className="panel">
          <h2>高意向机会</h2>
          <p className="panel__subtle">报价、合作、推进等信号最浓的联系人，适合优先跟。</p>
          <SignalList
            emptyText="暂无明显商业机会"
            items={topOpportunities}
            renderBody={(item) => (
              <li className="signal-list__item" key={`${item.contact_name}-${item.stage}`}>
                <SignalTitleRow
                  title={item.contact_name}
                  pill={<SignalPill tone="sea">机会分 {item.opportunity_score}</SignalPill>}
                />
                <div className="signal-list__body">
                  机会分 {item.opportunity_score} · 报价 {item.quote_signal_count} · 商业 {item.business_signal_count}
                </div>
                <div className="signal-list__meta">
                  {formatRoleLabel(item.role)} · {formatStageLabel(item.stage)}
                </div>
              </li>
            )}
          />
        </article>
        <article className="panel">
          <h2>售后风险</h2>
          <p className="panel__subtle">抱怨、异常、负面情绪偏多的对象，建议单独观察。</p>
          <SignalList
            emptyText="暂无明显售后风险"
            items={topRisks}
            renderBody={(item) => (
              <li className="signal-list__item" key={`${item.contact_name}-${item.stage}`}>
                <SignalTitleRow
                  title={item.contact_name}
                  pill={<SignalPill tone="rose">风险分 {item.risk_score}</SignalPill>}
                />
                <div className="signal-list__body">
                  风险分 {item.risk_score} · 报错 {item.support_signal_count} · 负面 {item.negative_signal_count}
                </div>
                <div className="signal-list__meta">
                  {formatRoleLabel(item.role)} · {formatStageLabel(item.stage)}
                </div>
              </li>
            )}
          />
        </article>
        <article className="panel">
          <h2>待跟进客户</h2>
          <p className="panel__subtle">从客户维度聚合出的待处理项，避免遗漏重要推进对象。</p>
          <SignalList
            emptyText="暂无待跟进客户"
            items={customerFollowups}
            renderBody={(item) => (
              <li className="signal-list__item" key={`${item.contact_name}-${item.pending_followup?.datetime}`}>
                <SignalTitleRow
                  title={item.contact_name}
                  pill={<SignalPill tone="gold">{(item.pending_followup?.labels || [])[0] || "待跟进"}</SignalPill>}
                />
                <div className="signal-list__body">{item.pending_followup?.content || ""}</div>
                <div className="signal-list__meta">
                  {(item.pending_followup?.labels || []).join(" / ")} · {formatDisplayDateTime(item.pending_followup?.datetime)}
                </div>
              </li>
            )}
          />
        </article>
      </section>
    </>
  );
}

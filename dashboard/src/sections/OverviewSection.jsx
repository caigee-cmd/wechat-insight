import {
  BarList,
  BulletList,
  MetaList,
  SectionKicker,
  SummaryGrid,
  TrendChart,
} from "../components/dashboardPrimitives";

export default function OverviewSection({
  labelMetaRows,
  peakDay,
  roleRows,
  summaryLines,
  windowLabel,
  windowRows,
  windowSummaryRows,
}) {
  return (
    <>
      <SectionKicker title="Overview" subtitle="先看这段时间你最值得关注的聊天摘要" />
      <section className="content-grid content-grid--overview">
        <article className="panel panel--wide">
          <h2>一句话摘要</h2>
          <p className="panel__subtle">把当期最浓缩的会话结论放在前面，方便你快速判断今天发生了什么。</p>
          <BulletList emptyText="暂无摘要" items={summaryLines} />
        </article>
        <article className="panel panel--wide">
          <div className="panel__header">
            <div>
              <h2>{windowLabel}趋势</h2>
              <p className="panel__subtle">
                峰值日期：{peakDay?.date || "暂无"} · 峰值消息：{peakDay?.total_messages || 0}
              </p>
            </div>
          </div>
          <SummaryGrid rows={windowSummaryRows} />
          <div className="chart-grid">
            <TrendChart accent="sea" emptyText="暂无趋势数据" metricKey="total_messages" rows={windowRows} title="消息量走势" />
            <TrendChart accent="gold" emptyText="暂无信号数据" metricKey="business_signal_count" rows={windowRows} title="商业信号走势" />
          </div>
        </article>
        <article className="panel">
          <h2>角色分布</h2>
          <p className="panel__subtle">从联系人类型看，你当前的沟通资源更偏业务还是偏日常。</p>
          <BarList emptyText="暂无角色数据" items={roleRows} suffix=" 人" />
        </article>
        <article className="panel">
          <h2>标签状态</h2>
          <p className="panel__subtle">标签联系人、自动建议和私聊联系人数量，用于判断特征层完整度。</p>
          <MetaList emptyText="暂无标签信息" rows={labelMetaRows} />
        </article>
      </section>
    </>
  );
}

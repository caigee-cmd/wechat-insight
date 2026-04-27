import {
  BarList,
  MetaList,
  RelationshipMap,
  SectionKicker,
  StoryDeck,
} from "../components/dashboardPrimitives";

export default function ActivitySection({
  chatLeaderboard,
  contactLeaderboard,
  filteredDailyRows,
  isRelationshipMapExpanded,
  onExpandRelationshipMap,
  overview,
  relationshipRows,
  showRelationshipMap,
  social,
  topChats,
  topContacts,
  topHours,
  viewStateIsFiltering,
  windowLabel,
}) {
  return (
    <>
      <SectionKicker title="Activity" subtitle="用趋势和活跃分布看清消息是怎么涌进来的" />
      <section className="content-grid content-grid--story">
        <article className="panel panel--wide-mobile">
          <div className="panel__header">
            <div>
              <h2>{windowLabel}日活明细</h2>
              <p className="panel__subtle">每天的峰值时段、最活跃会话和活跃范围。</p>
            </div>
          </div>
          <StoryDeck rows={filteredDailyRows} />
        </article>
        <article className="panel panel--wide-mobile">
          <div className="panel__header">
            <div>
              <h2>社交关系图</h2>
              <p className="panel__subtle">中心是你自己，上层是高频群聊，下层是高频私聊联系人，连线粗细代表互动密度。</p>
            </div>
          </div>
          {showRelationshipMap ? (
            <div className="reactbits-frame reactbits-frame--map">
              <RelationshipMap chatRows={chatLeaderboard} contactRows={contactLeaderboard} overview={overview} social={social} />
            </div>
          ) : (
            <div className="relationship-map-placeholder">
              <strong>{viewStateIsFiltering ? "筛选时已暂停关系图" : "关系图改成按需加载"}</strong>
              <p>
                {viewStateIsFiltering
                  ? "检索时先保留轻量列表，避免关系图跟着重算。清空检索后可继续查看。"
                  : "这块是当前最重的可视化，默认不挂载。需要时再手动展开。"}
              </p>
              <button
                className="relationship-map-placeholder__action"
                disabled={viewStateIsFiltering}
                onClick={onExpandRelationshipMap}
                type="button"
              >
                {isRelationshipMapExpanded ? "等待结束筛选" : "加载关系图"}
              </button>
            </div>
          )}
        </article>
      </section>
      <section className="content-grid content-grid--triple">
        <article className="panel">
          <h2>最活跃会话</h2>
          <p className="panel__subtle">消息最密集的场域，基本决定了你这段时间的注意力走向。</p>
          <BarList emptyText="暂无会话数据" items={topChats} suffix=" 条" />
        </article>
        <article className="panel">
          <h2>最活跃联系人</h2>
          <p className="panel__subtle">一对一关系里，谁占用了最多沟通带宽。</p>
          <BarList emptyText="暂无联系人数据" items={topContacts} suffix=" 条" />
        </article>
        <article className="panel">
          <h2>活跃时段</h2>
          <p className="panel__subtle">你最常进入高交流状态的时间窗口。</p>
          <BarList emptyText="暂无时段数据" items={topHours} suffix=" 条" />
        </article>
        <article className="panel panel--wide">
          <h2>关系摘要</h2>
          <p className="panel__subtle">用最少的字，把这张图想表达的重点读出来。</p>
          <MetaList emptyText="暂无关系图摘要" rows={relationshipRows} />
        </article>
      </section>
    </>
  );
}

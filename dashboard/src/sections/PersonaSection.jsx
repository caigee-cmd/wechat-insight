import {
  BarList,
  DeferredBlock,
  DimensionMatrix,
  EmotionDonut,
  FocusBoard,
  MetaList,
  ModeCard,
  PhraseCloud,
  SectionKicker,
  SignalList,
  SignalPill,
  SignalTitleRow,
  emotionTone,
} from "../components/dashboardPrimitives";

export default function PersonaSection({
  emotionDistribution,
  lifeModeRows,
  personaSnapshot,
  phraseItems,
  socialMetaRows,
  socialTopChats,
  topEmotionalChats,
  workModeRows,
  workModeToneValue,
  lifeModeToneValue,
  mbtiDimensions,
}) {
  return (
    <>
      <SectionKicker title="Persona" subtitle="让情绪、MBTI、口癖和社交节奏落到可视化上" />
      <FocusBoard
        cards={personaSnapshot.cards}
        eyebrow="Persona Snapshot"
        headline={personaSnapshot.headline}
        title="先看这 4 个观察点"
        tone="sea"
      />
      <section className="content-grid">
        <ModeCard emptyText="暂无工作人格样本" rows={workModeRows} title="工作人格" tone={emotionTone(workModeToneValue)} />
        <ModeCard emptyText="暂无日常人格样本" rows={lifeModeRows} title="日常人格" tone={emotionTone(lifeModeToneValue)} />
        <article className="panel">
          <h2>情绪分布</h2>
          <p className="panel__subtle">看你自己的表达更偏积极、平稳，还是容易带出焦虑和攻击性。</p>
          <div className="reactbits-frame reactbits-frame--analysis">
            <DeferredBlock isActiveTab label="情绪分布" minHeight={244}>
              <EmotionDonut distribution={emotionDistribution} />
            </DeferredBlock>
          </div>
        </article>
        <article className="panel">
          <h2>MBTI 推测</h2>
          <p className="panel__subtle">不是测试问卷，而是从真实聊天行为里逆推出的四维倾向。</p>
          <div className="reactbits-frame reactbits-frame--analysis">
            <DeferredBlock isActiveTab label="MBTI 推测" minHeight={284}>
              <DimensionMatrix dimensions={mbtiDimensions} />
            </DeferredBlock>
          </div>
        </article>
        <article className="panel">
          <h2>口癖统计</h2>
          <p className="panel__subtle">高频短语、反复出现的说法，会比单次措辞更像你。</p>
          <DeferredBlock isActiveTab label="口癖统计" minHeight={472}>
            <PhraseCloud items={phraseItems} />
          </DeferredBlock>
        </article>
        <article className="panel">
          <h2>社交节奏</h2>
          <p className="panel__subtle">用响应速度、群私聊占比和消息长度去看你的沟通方式。</p>
          <MetaList emptyText="暂无社交画像" rows={socialMetaRows} />
        </article>
        <article className="panel">
          <h2>情绪热点会话</h2>
          <p className="panel__subtle">不是最活跃，而是情绪浓度最高、最可能拉高心智负荷的会话。</p>
          <SignalList
            emptyText="暂无情绪热点会话"
            items={topEmotionalChats}
            renderBody={(item) => (
              <li className="signal-list__item" key={`${item.chat_name}-${item.emotion_score}`}>
                <SignalTitleRow
                  title={item.chat_name}
                  pill={
                    <SignalPill tone={Number(item.emotion_score) < 0 ? "rose" : "sea"}>
                      情绪分 {item.emotion_score}
                    </SignalPill>
                  }
                />
                <div className="signal-list__body">
                  情绪分 {item.emotion_score} · 积极 {item.positive} · 消极 {item.negative} · 愤怒 {item.angry}
                </div>
              </li>
            )}
          />
        </article>
        <article className="panel">
          <h2>社交高频会话</h2>
          <p className="panel__subtle">长期高频并不一定高价值，但一定会改变你的注意力结构。</p>
          <BarList emptyText="暂无会话画像数据" items={socialTopChats} suffix=" 条" />
        </article>
      </section>
    </>
  );
}

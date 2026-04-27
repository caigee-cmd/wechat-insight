import { MetaList, SectionKicker } from "../components/dashboardPrimitives";

export default function ArtifactsSection({ artifactRows }) {
  return (
    <>
      <SectionKicker title="Artifacts" subtitle="最后把导出结果和中间产物交代清楚" />
      <section className="content-grid">
        <article className="panel panel--wide">
          <h2>分析产物</h2>
          <p className="panel__subtle">导出链路中的关键产物路径，方便你继续追查或二次加工。</p>
          <MetaList emptyText="暂无产物信息" rows={artifactRows} />
        </article>
      </section>
    </>
  );
}

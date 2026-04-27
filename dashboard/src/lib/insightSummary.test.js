import test from "node:test";
import assert from "node:assert/strict";

import { buildPersonaSnapshot, buildSignalsSnapshot } from "./insightSummary.js";

test("buildSignalsSnapshot extracts the most actionable signal cards", () => {
  const snapshot = buildSignalsSnapshot({
    customerFollowups: [
      {
        contact_name: "产品经理A",
        pending_followup: {
          datetime: "2026-04-25 18:05:16",
          labels: ["排期"],
        },
      },
    ],
    dailyFollowups: [
      {
        chat_name: "陈毅",
        datetime: "2026-04-25 21:16:49",
        labels: ["问题", "商业"],
      },
    ],
    topOpportunities: [
      {
        contact_name: "陈毅",
        opportunity_score: 20,
        stage: "negotiating",
      },
    ],
    topRisks: [
      {
        contact_name: "弟弟",
        risk_score: 6,
        stage: "supporting",
      },
    ],
  });

  assert.equal(snapshot.headline, "先处理 陈毅，再推进高分机会和售后风险。");
  assert.deepEqual(
    snapshot.cards.map((item) => ({ detail: item.detail, label: item.label, value: item.value })),
    [
      { label: "最该先回", value: "陈毅", detail: "问题 / 商业 · 2026-04-25 21:16" },
      { label: "商机最高", value: "陈毅", detail: "机会分 20 · 推进中" },
      { label: "风险最高", value: "弟弟", detail: "风险分 6 · 售后处理中" },
      { label: "客户待办", value: "产品经理A", detail: "排期 · 2026-04-25 18:05" },
    ]
  );
});

test("buildPersonaSnapshot extracts the most representative persona cards", () => {
  const snapshot = buildPersonaSnapshot({
    overview: {
      dominant_emotion: "positive",
      mbti_type: "ENTJ",
    },
    social: {
      median_response_latency_minutes: 3.32,
      night_message_ratio: 0.018,
    },
    speech: {
      repeated_phrases: [{ count: 7, text: "对啊" }],
    },
    topEmotionalChats: [{ chat_name: "浪子 独自漂泊", emotion_score: -11 }],
  });

  assert.equal(snapshot.headline, "ENTJ 的执行感很强，情绪整体平稳，但有一个明显的负载源。");
  assert.deepEqual(
    snapshot.cards.map((item) => ({ detail: item.detail, label: item.label, value: item.value })),
    [
      { label: "人格定调", value: "ENTJ / 积极", detail: "当前主导人格与情绪底色" },
      { label: "最高频短语", value: "对啊", detail: "重复 7 次" },
      { label: "情绪负载源", value: "浪子 独自漂泊", detail: "情绪分 -11" },
      { label: "沟通节奏", value: "3.32 分钟", detail: "夜间占比 1.8%" },
    ]
  );
});

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildHeroRows,
  buildMetricCards,
  buildOrbitRows,
  buildRibbonRows,
} from "./dashboardChrome.js";

test("buildMetricCards returns the fixed dashboard KPI deck", () => {
  assert.deepEqual(
    buildMetricCards({
      active_chat_count: 56,
      business_contact_count: 31,
      pending_followup_count: 7,
      text_messages: 3564,
      total_messages: 4925,
      total_private_contacts: 32,
    }),
    [
      { detail: "全量会话脉冲", label: "总消息", tone: "ink", value: 4925 },
      { detail: "可解析语义样本", label: "文本消息", tone: "sea", value: 3564 },
      { detail: "本周期触达范围", label: "活跃会话", tone: "gold", value: 56 },
      { detail: "一对一关系池", label: "私聊联系人", tone: "ink", value: 32 },
      { detail: "高意向客群", label: "商机联系人", tone: "sea", value: 31 },
      { detail: "需要继续推进", label: "待跟进", tone: "gold", value: 7 },
    ]
  );
});

test("buildHeroRows and buildOrbitRows keep top chrome data compact", () => {
  assert.deepEqual(
    buildHeroRows({
      emotionLabel: "积极",
      emotionTone: "sea",
      mbtiType: "ENTJ",
      medianResponseText: "3.32 分钟",
      overviewDays: 2,
    }),
    [
      ["观察区间", "2 天", "ink"],
      ["人格推测", "ENTJ", "sea"],
      ["情绪底色", "积极", "sea"],
      ["响应时延", "3.32 分钟", "gold"],
    ]
  );

  assert.deepEqual(
    buildOrbitRows({
      avgMessageLength: "6.27",
      generatedAt: "2026-04-27 09:35",
      groupMessageCount: "4256",
      privateMessageCount: "669",
    }),
    [
      ["群聊消息", "4256"],
      ["私聊消息", "669"],
      ["平均长度", "6.27"],
      ["生成时间", "2026-04-27 09:35"],
    ]
  );
});

test("buildRibbonRows filters empty entries and preserves business highlights", () => {
  assert.deepEqual(
    buildRibbonRows({
      busiestBusinessChatName: "CodeFree售后群",
      busiestSupportChatName: "小程序互帮互助 4 群",
      dominantEmotionLabel: "积极",
      mbtiType: "ENTJ",
      medianResponseText: "3.32 分钟",
      nightRatioText: "1.8%",
      topContactName: "陈毅",
      topGroupName: "小程序互帮互助 4 群",
    }),
    [
      ["最强群聊", "小程序互帮互助 4 群"],
      ["最强私聊", "陈毅"],
      ["商业密度群", "CodeFree售后群"],
      ["售后压力群", "小程序互帮互助 4 群"],
      ["主导情绪", "积极"],
      ["人格推测", "ENTJ"],
      ["中位响应", "3.32 分钟"],
      ["夜间占比", "1.8%"],
    ]
  );
});

import test from "node:test";
import assert from "node:assert/strict";

import { buildRelationshipSphereModel } from "./relationshipSphere.js";

function magnitude(point) {
  return Math.sqrt(point.x ** 2 + point.y ** 2 + point.z ** 2);
}

test("buildRelationshipSphereModel keeps nodes on a sphere and splits groups from contacts", () => {
  const model = buildRelationshipSphereModel({
    chatRows: [
      { chat_id: "g-1", chat_name: "群 A", chat_type: "group", total_messages: 320 },
      { chat_id: "g-2", chat_name: "群 B", chat_type: "group", total_messages: 180 },
      { chat_id: "dm-ignored", chat_name: "非群聊", chat_type: "direct", total_messages: 999 },
    ],
    contactRows: [
      { contact_id: "c-1", contact_name: "联系人 A", total_messages: 92 },
      { contact_id: "c-2", contact_name: "联系人 B", total_messages: 48 },
    ],
    overview: {
      total_messages: 4925,
      business_contact_count: 31,
      date_span_days: 2,
      mbti_type: "ENTJ",
      dominant_emotion: "positive",
    },
    social: {
      median_response_latency_minutes: 3.32,
      private_message_count: 669,
    },
    radius: 2.2,
  });

  const groups = model.nodes.filter((node) => node.kind === "group");
  const contacts = model.nodes.filter((node) => node.kind === "contact");

  assert.equal(groups.length, 2);
  assert.equal(contacts.length, 2);
  assert.ok(groups.every((node) => node.position.y > 0));
  assert.ok(contacts.every((node) => node.position.y < 0));
  assert.ok(model.nodes.every((node) => Math.abs(magnitude(node.position) - 2.2) < 1e-9));
  assert.equal(model.defaultState.title, "将鼠标移到球体节点上");
});

test("buildRelationshipSphereModel scales dominant nodes and preserves inspector data", () => {
  const model = buildRelationshipSphereModel({
    chatRows: [
      {
        chat_id: "g-1",
        chat_name: "高频群聊",
        chat_type: "group",
        total_messages: 400,
        business_signal_count: 5,
        support_signal_count: 2,
        active_days: 4,
        avg_message_length: 28.6,
        last_active_at: "2026-04-27 21:00:00",
        self_ratio: 0.12,
      },
      {
        chat_id: "g-2",
        chat_name: "低频群聊",
        chat_type: "group",
        total_messages: 100,
        business_signal_count: 1,
        support_signal_count: 0,
        active_days: 2,
        avg_message_length: 14.2,
        last_active_at: "2026-04-27 18:00:00",
        self_ratio: 0.04,
      },
    ],
    contactRows: [
      {
        contact_id: "c-1",
        contact_name: "高频联系人",
        total_messages: 88,
        business_signal_count: 2,
        support_signal_count: 1,
        active_days: 3,
        question_ratio: 0.18,
        self_ratio: 0.64,
      },
    ],
    overview: {
      total_messages: 4925,
      business_contact_count: 31,
      date_span_days: 2,
      mbti_type: "ENTJ",
      dominant_emotion: "positive",
    },
    social: {
      median_response_latency_minutes: 3.32,
      private_message_count: 669,
    },
  });

  const topGroup = model.nodes.find((node) => node.id === "g-1");
  const smallGroup = model.nodes.find((node) => node.id === "g-2");
  const topContact = model.nodes.find((node) => node.id === "c-1");

  assert.ok(topGroup.size > smallGroup.size);
  assert.ok(topGroup.lineOpacity > smallGroup.lineOpacity);
  assert.equal(topGroup.state.type, "高频群聊");
  assert.match(topGroup.state.summary, /最近 2026-04-27 21:00:00/);
  assert.equal(topContact.state.type, "高频私聊");
  assert.equal(topContact.state.selfRatio, "64.0%");
});

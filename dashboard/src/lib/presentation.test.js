import test from "node:test";
import assert from "node:assert/strict";

import {
  formatDisplayDateTime,
  formatRoleLabel,
  formatStageLabel,
  readInitialUiState,
  writeUiStateQuery,
} from "./presentation.js";

test("formatRoleLabel translates known role codes", () => {
  assert.equal(formatRoleLabel("customer"), "客户");
  assert.equal(formatRoleLabel("vendor"), "供应方");
  assert.equal(formatRoleLabel("unknown"), "未知");
});

test("formatStageLabel translates known stage codes", () => {
  assert.equal(formatStageLabel("negotiating"), "推进中");
  assert.equal(formatStageLabel("follow_up"), "待跟进");
  assert.equal(formatStageLabel("supporting"), "售后处理中");
  assert.equal(formatStageLabel("unknown"), "未知");
});

test("formatDisplayDateTime compacts ISO timestamps for Chinese UI", () => {
  assert.equal(formatDisplayDateTime("2026-04-27T09:35:50"), "2026-04-27 09:35");
  assert.equal(formatDisplayDateTime(""), "--");
});

test("readInitialUiState keeps only supported query params", () => {
  const state = readInitialUiState("?tab=signals&window=7d&q=%E5%AE%A2%E6%88%B7&unused=1");
  assert.deepEqual(state, {
    activeTab: "signals",
    query: "客户",
    windowId: "7d",
  });
});

test("writeUiStateQuery persists non-default UI state", () => {
  const nextQuery = writeUiStateQuery({
    activeTab: "persona",
    baseSearch: "?foo=bar",
    query: "ENTJ",
    windowId: "30d",
  });

  assert.equal(nextQuery, "?foo=bar&tab=persona&window=30d&q=ENTJ");
});

import test from "node:test";
import assert from "node:assert/strict";

import { buildDashboardViewState } from "./dashboardViewState.js";

test("buildDashboardViewState keeps dashboard in steady mode by default", () => {
  assert.deepEqual(buildDashboardViewState(""), {
    isFiltering: false,
    shellClassName: "page-shell page-shell--steady",
  });
});

test("buildDashboardViewState marks filtering mode when query has content", () => {
  assert.deepEqual(buildDashboardViewState("  客户  "), {
    isFiltering: true,
    shellClassName: "page-shell page-shell--steady page-shell--filtering",
  });
});

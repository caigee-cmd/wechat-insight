import test from "node:test";
import assert from "node:assert/strict";

import { buildActiveTabData, shouldRenderRelationshipMap } from "./dashboardTabState.js";

test("buildActiveTabData only invokes the active tab builder", () => {
  const calls = [];

  const result = buildActiveTabData("signals", {
    activity: () => {
      calls.push("activity");
      return { id: "activity" };
    },
    overview: () => {
      calls.push("overview");
      return { id: "overview" };
    },
    persona: () => {
      calls.push("persona");
      return { id: "persona" };
    },
    signals: () => {
      calls.push("signals");
      return { id: "signals" };
    },
  });

  assert.deepEqual(calls, ["signals"]);
  assert.deepEqual(result, { id: "signals" });
});

test("buildActiveTabData falls back to an empty object for unknown tabs", () => {
  assert.deepEqual(buildActiveTabData("unknown", {}), {});
});

test("shouldRenderRelationshipMap only enables the graph in steady activity mode", () => {
  assert.equal(
    shouldRenderRelationshipMap({ activeTab: "activity", isFiltering: false, isExpanded: true }),
    true
  );
  assert.equal(
    shouldRenderRelationshipMap({ activeTab: "activity", isFiltering: true, isExpanded: true }),
    false
  );
  assert.equal(
    shouldRenderRelationshipMap({ activeTab: "signals", isFiltering: false, isExpanded: true }),
    false
  );
  assert.equal(
    shouldRenderRelationshipMap({ activeTab: "activity", isFiltering: false, isExpanded: false }),
    false
  );
});

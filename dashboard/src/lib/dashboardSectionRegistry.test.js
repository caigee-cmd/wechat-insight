import test from "node:test";
import assert from "node:assert/strict";

import {
  getNearbySectionIds,
  SECTION_LOADERS,
  SECTION_ORDER,
  resolveDashboardSectionId,
} from "./dashboardSectionRegistry.js";

test("resolveDashboardSectionId keeps known tabs and falls back to overview", () => {
  assert.equal(resolveDashboardSectionId("persona"), "persona");
  assert.equal(resolveDashboardSectionId("unknown"), "overview");
});

test("SECTION_LOADERS exposes one lazy loader per dashboard tab", () => {
  assert.deepEqual(Object.keys(SECTION_LOADERS), [
    "overview",
    "activity",
    "signals",
    "persona",
    "artifacts",
  ]);
  assert.deepEqual(SECTION_ORDER, Object.keys(SECTION_LOADERS));

  for (const loader of Object.values(SECTION_LOADERS)) {
    assert.equal(typeof loader, "function");
  }
});

test("getNearbySectionIds only returns adjacent dashboard sections", () => {
  assert.deepEqual(getNearbySectionIds("overview"), ["activity"]);
  assert.deepEqual(getNearbySectionIds("signals"), ["activity", "persona"]);
  assert.deepEqual(getNearbySectionIds("artifacts"), ["persona"]);
  assert.deepEqual(getNearbySectionIds("unknown"), ["activity"]);
});

import test from "node:test";
import assert from "node:assert/strict";

import { shouldMountDeferredBlock } from "./deferredBlockState.js";

test("shouldMountDeferredBlock waits for active view and viewport entry", () => {
  assert.equal(
    shouldMountDeferredBlock({ hasEnteredViewport: false, hasMounted: false, isActiveTab: true }),
    false
  );
  assert.equal(
    shouldMountDeferredBlock({ hasEnteredViewport: true, hasMounted: false, isActiveTab: false }),
    false
  );
  assert.equal(
    shouldMountDeferredBlock({ hasEnteredViewport: true, hasMounted: false, isActiveTab: true }),
    true
  );
});

test("shouldMountDeferredBlock keeps mounted blocks alive after first hydration", () => {
  assert.equal(
    shouldMountDeferredBlock({ hasEnteredViewport: false, hasMounted: true, isActiveTab: true }),
    true
  );
});

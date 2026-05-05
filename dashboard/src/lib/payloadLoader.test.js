import test from "node:test";
import assert from "node:assert/strict";

import { buildPayloadUrl, loadDashboardPayload, readEmbeddedPayload } from "./payloadLoader.js";

test("readEmbeddedPayload parses the embedded dashboard payload", () => {
  const documentRef = {
    getElementById(id) {
      assert.equal(id, "report-payload");
      return {
        textContent: JSON.stringify({
          schema_version: "report-data.v1",
          overview: { total_messages: 3 },
        }),
      };
    },
  };

  assert.deepEqual(readEmbeddedPayload(documentRef), {
    schema_version: "report-data.v1",
    overview: { total_messages: 3 },
  });
});

test("loadDashboardPayload prefers embedded payload over network fetch", async () => {
  const payload = {
    schema_version: "report-data.v1",
    overview: { total_messages: 3 },
  };
  const documentRef = {
    getElementById() {
      return { textContent: JSON.stringify(payload) };
    },
  };

  const result = await loadDashboardPayload({
    documentRef,
    fetchImpl() {
      throw new Error("fetch should not be called");
    },
  });

  assert.deepEqual(result, payload);
});

test("buildPayloadUrl uses the configured dashboard base path", () => {
  assert.equal(
    buildPayloadUrl({ basePath: "./", cacheBust: 123 }),
    "./report_payload.json?t=123"
  );
});

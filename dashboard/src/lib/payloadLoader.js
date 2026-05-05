export function readEmbeddedPayload(documentRef) {
  const resolvedDocument = documentRef || (typeof document !== "undefined" ? document : null);
  const element = resolvedDocument?.getElementById?.("report-payload");
  const text = element?.textContent?.trim();
  if (!text) {
    return null;
  }
  return JSON.parse(text);
}

export function getRuntimeBasePath() {
  return import.meta.env?.BASE_URL || "/";
}

export function buildPayloadUrl({ basePath = getRuntimeBasePath(), cacheBust = Date.now() } = {}) {
  const normalizedBase = basePath.endsWith("/") ? basePath : `${basePath}/`;
  return `${normalizedBase}report_payload.json?t=${encodeURIComponent(cacheBust)}`;
}

export async function loadDashboardPayload({
  documentRef,
  fetchImpl,
  basePath,
  cacheBust,
} = {}) {
  const embeddedPayload = readEmbeddedPayload(documentRef);
  if (embeddedPayload) {
    return embeddedPayload;
  }

  const resolvedFetch = fetchImpl || (typeof fetch !== "undefined" ? fetch : null);
  if (!resolvedFetch) {
    throw new Error("fetch unavailable");
  }

  const response = await resolvedFetch(buildPayloadUrl({
    basePath: basePath ?? getRuntimeBasePath(),
    cacheBust: cacheBust ?? Date.now(),
  }));
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

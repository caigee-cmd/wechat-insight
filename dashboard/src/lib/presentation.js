const ROLE_LABELS = {
  customer: "客户",
  vendor: "供应方",
  unknown: "未知",
};

const STAGE_LABELS = {
  negotiating: "推进中",
  follow_up: "待跟进",
  supporting: "售后处理中",
  unknown: "未知",
};

const VALID_TABS = new Set(["overview", "activity", "signals", "persona", "artifacts"]);
const VALID_WINDOWS = new Set(["all", "7d", "30d"]);

export function formatRoleLabel(value) {
  return ROLE_LABELS[value] || value || "未知";
}

export function formatStageLabel(value) {
  return STAGE_LABELS[value] || value || "未知";
}

export function formatDisplayDateTime(value) {
  const text = String(value || "").trim();
  if (!text) {
    return "--";
  }

  const match = text.match(/^(\d{4}-\d{2}-\d{2})[T\s](\d{2}:\d{2})/);
  if (match) {
    return `${match[1]} ${match[2]}`;
  }

  return text;
}

export function readInitialUiState(search = "") {
  const params = new URLSearchParams(search || "");
  const activeTab = params.get("tab");
  const windowId = params.get("window");

  return {
    activeTab: VALID_TABS.has(activeTab) ? activeTab : "overview",
    query: params.get("q") || "",
    windowId: VALID_WINDOWS.has(windowId) ? windowId : "all",
  };
}

export function writeUiStateQuery({ activeTab, baseSearch = "", query, windowId }) {
  const params = new URLSearchParams(baseSearch || "");

  params.delete("tab");
  params.delete("window");
  params.delete("q");

  if (VALID_TABS.has(activeTab) && activeTab !== "overview") {
    params.set("tab", activeTab);
  }

  if (VALID_WINDOWS.has(windowId) && windowId !== "all") {
    params.set("window", windowId);
  }

  const safeQuery = String(query || "").trim();
  if (safeQuery) {
    params.set("q", safeQuery);
  }

  const nextQuery = params.toString();
  return nextQuery ? `?${nextQuery}` : "";
}

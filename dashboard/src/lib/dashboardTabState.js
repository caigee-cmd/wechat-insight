export function buildActiveTabData(activeTab, builders) {
  const build = builders?.[activeTab];
  if (typeof build !== "function") {
    return {};
  }
  return build();
}

export function shouldRenderRelationshipMap({ activeTab, isExpanded, isFiltering }) {
  return activeTab === "activity" && Boolean(isExpanded) && !isFiltering;
}

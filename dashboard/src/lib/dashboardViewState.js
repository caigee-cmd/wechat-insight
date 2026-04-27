export function buildDashboardViewState(query) {
  const isFiltering = String(query || "").trim().length > 0;
  return {
    isFiltering,
    shellClassName: [
      "page-shell",
      "page-shell--steady",
      isFiltering ? "page-shell--filtering" : "",
    ]
      .filter(Boolean)
      .join(" "),
  };
}

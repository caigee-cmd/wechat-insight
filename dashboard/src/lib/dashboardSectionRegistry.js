const SECTION_LOADERS = {
  overview: () => import("../sections/OverviewSection.jsx"),
  activity: () => import("../sections/ActivitySection.jsx"),
  signals: () => import("../sections/SignalsSection.jsx"),
  persona: () => import("../sections/PersonaSection.jsx"),
  artifacts: () => import("../sections/ArtifactsSection.jsx"),
};

const SECTION_ORDER = Object.keys(SECTION_LOADERS);
const PRELOAD_CACHE = new Map();

function resolveDashboardSectionId(sectionId) {
  return Object.hasOwn(SECTION_LOADERS, sectionId) ? sectionId : "overview";
}

function getNearbySectionIds(sectionId) {
  const resolvedSectionId = resolveDashboardSectionId(sectionId);
  const index = SECTION_ORDER.indexOf(resolvedSectionId);
  return [SECTION_ORDER[index - 1], SECTION_ORDER[index + 1]].filter(Boolean);
}

function preloadDashboardSection(sectionId) {
  const resolvedSectionId = resolveDashboardSectionId(sectionId);
  if (!PRELOAD_CACHE.has(resolvedSectionId)) {
    PRELOAD_CACHE.set(resolvedSectionId, SECTION_LOADERS[resolvedSectionId]());
  }
  return PRELOAD_CACHE.get(resolvedSectionId);
}

export {
  getNearbySectionIds,
  preloadDashboardSection,
  SECTION_LOADERS,
  SECTION_ORDER,
  resolveDashboardSectionId,
};

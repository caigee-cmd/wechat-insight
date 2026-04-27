export function shouldMountDeferredBlock({ hasEnteredViewport, hasMounted, isActiveTab }) {
  return Boolean(isActiveTab) && (Boolean(hasMounted) || Boolean(hasEnteredViewport));
}

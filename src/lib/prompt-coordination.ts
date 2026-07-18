export const FIRST_VISIT_THANKS_EVENT = "rv:first-visit-thanks-visibility";
const FIRST_VISIT_THANKS_ATTRIBUTE = "data-first-visit-thanks-open";

export function isFirstVisitThanksOpen() {
  return typeof document !== "undefined"
    && document.documentElement.hasAttribute(FIRST_VISIT_THANKS_ATTRIBUTE);
}

export function setFirstVisitThanksOpen(open: boolean) {
  if (typeof document === "undefined" || typeof window === "undefined") return;
  document.documentElement.toggleAttribute(FIRST_VISIT_THANKS_ATTRIBUTE, open);
  window.dispatchEvent(new CustomEvent(FIRST_VISIT_THANKS_EVENT, { detail: open }));
}

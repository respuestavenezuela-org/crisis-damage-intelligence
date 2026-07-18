import type { Language } from "@/components/types";

const LANG_STORAGE_KEY = "rv-lang";
export const LANG_EVENT = "rv:language";
export const DEFAULT_LANGUAGE: Language = "es";

export function readStoredLang(): Language {
  if (typeof window === "undefined") return DEFAULT_LANGUAGE;
  try {
    const stored = window.localStorage.getItem(LANG_STORAGE_KEY);
    if (stored === "es" || stored === "en") return stored;
  } catch {
    // Some embedded/private browser contexts deny storage; Spanish remains the safe default.
  }
  return DEFAULT_LANGUAGE;
}

export function subscribeStoredLang(onChange: () => void) {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(LANG_EVENT, onChange);
  return () => window.removeEventListener(LANG_EVENT, onChange);
}

export function persistLang(language: Language) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LANG_STORAGE_KEY, language);
  } catch {
    // Keep the in-memory UI switch usable when persistence is blocked.
  }
  window.dispatchEvent(new CustomEvent(LANG_EVENT, { detail: language }));
}

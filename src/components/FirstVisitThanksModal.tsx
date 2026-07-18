"use client";

import { useCallback, useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { DEFAULT_LANGUAGE, readStoredLang, subscribeStoredLang } from "@/lib/lang";
import { setFirstVisitThanksOpen } from "@/lib/prompt-coordination";

const DISMISS_STORAGE_KEY = "respuesta-venezuela:first-visit-thanks-dismissed:v1";
const COPY = {
  es: {
    close: "Cerrar",
    closeAria: "Cerrar agradecimiento",
    title: "Gracias por ayudar a las comunidades afectadas.",
    description: "Este mapa fue preparado para apoyar una respuesta cuidadosa, clara y basada en fuentes verificables.",
    confirm: "Entendido",
  },
  en: {
    close: "Close",
    closeAria: "Close thank-you message",
    title: "Thank you for helping affected communities.",
    description: "This map was prepared to support a careful, clear, and source-based response.",
    confirm: "Got it",
  },
};

function readDismissed() {
  try {
    return window.localStorage.getItem(DISMISS_STORAGE_KEY) === "1";
  } catch {
    try {
      return window.sessionStorage.getItem(DISMISS_STORAGE_KEY) === "1";
    } catch {
      return false;
    }
  }
}

function writeDismissed() {
  try {
    window.localStorage.setItem(DISMISS_STORAGE_KEY, "1");
    return;
  } catch {
    // Some field browsers disable persistent storage. Session storage still
    // prevents repeat prompts during the same visit when available.
  }

  try {
    window.sessionStorage.setItem(DISMISS_STORAGE_KEY, "1");
  } catch {
    // Closing in component state is still enough for the active page view.
  }
}

export default function FirstVisitThanksModal() {
  const language = useSyncExternalStore(subscribeStoredLang, readStoredLang, () => DEFAULT_LANGUAGE);
  const t = COPY[language];
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const primaryButtonRef = useRef<HTMLButtonElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  const dismiss = useCallback(() => {
    writeDismissed();
    setFirstVisitThanksOpen(false);
    setIsVisible(false);
    restoreFocusRef.current?.focus();
  }, []);

  useEffect(() => {
    if (readDismissed()) return;
    setFirstVisitThanksOpen(true);
    const openTimer = window.setTimeout(() => {
      restoreFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setIsVisible(true);
    }, 0);
    return () => {
      window.clearTimeout(openTimer);
      setFirstVisitThanksOpen(false);
    };
  }, []);

  useEffect(() => {
    if (!isVisible) return;

    primaryButtonRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        dismiss();
        return;
      }

      if (event.key !== "Tab" || !dialogRef.current) return;

      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => !element.hasAttribute("disabled") && !element.getAttribute("aria-hidden"));

      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [dismiss, isVisible]);

  if (!isVisible) return null;

  return (
    <div
      className="fixed inset-0 z-[1300] grid place-items-center bg-[#11120f]/55 px-4 py-6 backdrop-blur-[2px]"
      data-testid="first-visit-thanks-modal"
      role="presentation"
    >
      <div
        ref={dialogRef}
        aria-describedby={descriptionId}
        aria-labelledby={titleId}
        aria-modal="true"
        className="relative w-full max-w-[390px] rounded-lg border border-[#bdb7a8] bg-[#fffdf8] p-5 text-[#171816] shadow-[0_22px_60px_rgba(0,0,0,.30)]"
        role="dialog"
      >
        <button
          aria-label={t.closeAria}
          className="absolute right-3 top-3 min-h-10 rounded-md border border-transparent px-3 text-sm font-bold text-[#676b64] hover:border-[#bdb7a8] hover:bg-[#f7f4ec]"
          onClick={dismiss}
          style={{ color: "#676b64" }}
          type="button"
        >
          {t.close}
        </button>

        <p className="mb-2 pr-20 text-xs font-extrabold uppercase tracking-[0.04em] text-[#1f6f56]">
          Respuesta Venezuela
        </p>
        <h2 id={titleId} className="mb-3 pr-10 text-xl font-extrabold leading-tight">
          {t.title}
        </h2>
        <p id={descriptionId} className="mb-5 text-sm leading-6 text-[#4c514b]">
          {t.description}
        </p>
        <button
          ref={primaryButtonRef}
          className="min-h-11 w-full rounded-md bg-[#11120f] px-4 py-2 text-sm font-extrabold text-[#fffdf8] hover:bg-[#2a2c27]"
          onClick={dismiss}
          style={{ color: "#fffdf8" }}
          type="button"
        >
          {t.confirm}
        </button>
      </div>
    </div>
  );
}

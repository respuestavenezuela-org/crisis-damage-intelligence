"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { LANG_EVENT, readStoredLang } from "@/lib/lang";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISS_KEY = "rv-install-dismissed-at";
const SNOOZE_MS = 7 * 24 * 60 * 60 * 1000;
const OFFSET_VAR = "--install-bar";

type Lang = "es" | "en";
type Mode = "native" | "ios" | "manual";

const COPY: Record<Lang, { lead: string; cta: string; iosHint: string; manualHint: string; later: string; aria: string }> = {
  es: {
    lead: "Instálala en tu teléfono para abrirla como app",
    cta: "Instalar app",
    iosHint: "Toca Compartir y luego “Agregar a inicio”.",
    manualHint: "Abre el menú del navegador y elige “Instalar app”.",
    later: "Ahora no",
    aria: "Instalar la aplicación",
  },
  en: {
    lead: "Install it on your phone to open it as an app",
    cta: "Install app",
    iosHint: "Tap Share, then “Add to Home Screen”.",
    manualHint: "Open the browser menu and choose “Install app”.",
    later: "Not now",
    aria: "Install the application",
  },
};

function isStandalone() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

function dismissedRecently() {
  try {
    const dismissedAt = Number(localStorage.getItem(DISMISS_KEY) ?? 0);
    return Boolean(dismissedAt && Date.now() - dismissedAt < SNOOZE_MS);
  } catch {
    return false;
  }
}

function isIos() {
  const ua = window.navigator.userAgent;
  const iOSDevice = /iphone|ipad|ipod/i.test(ua);
  const iPadOS = /macintosh/i.test(ua) && navigator.maxTouchPoints > 1;
  return iOSDevice || iPadOS;
}

function initialMode(): Mode | null {
  if (typeof window === "undefined") return null;
  if (isStandalone() || dismissedRecently()) return null;
  return isIos() ? "ios" : "manual";
}

export default function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [lang, setLang] = useState<Lang>("es");
  const barRef = useRef<HTMLDivElement | null>(null);
  const visible = mode !== null;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const canPrompt = !isStandalone() && !dismissedRecently();
    const initialStateFrame = requestAnimationFrame(() => {
      setLang(readStoredLang());
      setMode(canPrompt ? initialMode() : null);
    });
    if (!canPrompt) return () => cancelAnimationFrame(initialStateFrame);

    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setDeferred(event as BeforeInstallPromptEvent);
      setMode("native");
    };
    const onInstalled = () => {
      setMode(null);
      setDeferred(null);
    };
    const onLangChange = (event: Event) => {
      const next = (event as CustomEvent).detail;
      if (next === "es" || next === "en") setLang(next);
    };

    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    window.addEventListener(LANG_EVENT, onLangChange);
    return () => {
      cancelAnimationFrame(initialStateFrame);
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
      window.removeEventListener(LANG_EVENT, onLangChange);
    };
  }, []);

  useLayoutEffect(() => {
    const root = document.documentElement;
    if (!visible || !barRef.current) {
      root.style.setProperty(OFFSET_VAR, "0px");
      return;
    }
    const apply = () => {
      const height = barRef.current?.offsetHeight ?? 0;
      root.style.setProperty(OFFSET_VAR, `${height}px`);
    };
    apply();
    window.addEventListener("resize", apply);
    return () => {
      window.removeEventListener("resize", apply);
      root.style.setProperty(OFFSET_VAR, "0px");
    };
  }, [visible, mode, lang]);

  if (!visible || !mode) return null;

  const t = COPY[lang];

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setMode(null);
  };

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    const { outcome } = await deferred.userChoice;
    if (outcome === "accepted") setMode(null);
    else dismiss();
    setDeferred(null);
  };

  const hint = mode === "ios" ? t.iosHint : mode === "manual" ? t.manualHint : null;

  return (
    <div ref={barRef} className="install-prompt" role="dialog" aria-label={t.aria}>
      <div className="install-prompt-icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <rect x="6" y="2.5" width="12" height="19" rx="2.4" stroke="currentColor" strokeWidth="1.6" />
          <line x1="10" y1="18.5" x2="14" y2="18.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </div>
      <div className="install-prompt-text">
        <strong>{t.lead}</strong>
        {hint ? <span>{hint}</span> : null}
      </div>
      <div className="install-prompt-actions">
        {mode === "native" ? (
          <button type="button" className="install-prompt-cta" onClick={install}>
            {t.cta}
          </button>
        ) : null}
        <button type="button" className="install-prompt-later" onClick={dismiss} aria-label={t.later}>
          {mode === "native" ? t.later : "✕"}
        </button>
      </div>
    </div>
  );
}

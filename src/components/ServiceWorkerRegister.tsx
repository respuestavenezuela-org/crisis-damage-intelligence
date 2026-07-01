"use client";

import { useEffect, useState } from "react";
import { LANG_EVENT, readStoredLang } from "@/lib/lang";

type Lang = "es" | "en";

const COPY: Record<Lang, { msg: string; action: string; aria: string }> = {
  es: { msg: "Nueva versión disponible", action: "Actualizar", aria: "Actualización disponible" },
  en: { msg: "New version available", action: "Update", aria: "Update available" },
};

export default function ServiceWorkerRegister() {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null);
  const [lang, setLang] = useState<Lang>(() => readStoredLang());

  useEffect(() => {
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;

    const onLang = (event: Event) => {
      const next = (event as CustomEvent).detail;
      if (next === "es" || next === "en") setLang(next);
    };
    window.addEventListener(LANG_EVENT, onLang);

    const hadController = Boolean(navigator.serviceWorker.controller);
    let refreshing = false;
    const onControllerChange = () => {
      if (refreshing || !hadController) return;
      refreshing = true;
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);

    let updateTimer: ReturnType<typeof setInterval> | undefined;
    const watch = (reg: ServiceWorkerRegistration) => {
      if (reg.waiting && navigator.serviceWorker.controller) setWaiting(reg.waiting);
      reg.addEventListener("updatefound", () => {
        const installing = reg.installing;
        if (!installing) return;
        installing.addEventListener("statechange", () => {
          if (installing.state === "installed" && navigator.serviceWorker.controller) {
            setWaiting(reg.waiting ?? installing);
          }
        });
      });
    };

    const cacheShell = () => {
      try {
        const urls = performance
          .getEntriesByType("resource")
          .map((entry) => entry.name)
          .filter((url) => url.includes("/_next/static/"))
          .map((url) => {
            try {
              return new URL(url).pathname;
            } catch {
              return null;
            }
          })
          .filter((url): url is string => Boolean(url));
        if (urls.length === 0) return;
        urls.push("/");
        navigator.serviceWorker.ready
          .then((reg) => {
            (reg.active ?? navigator.serviceWorker.controller)?.postMessage({
              type: "CACHE_SHELL",
              urls: [...new Set(urls)],
            });
          })
          .catch(() => {});
      } catch {
        // best effort
      }
    };

    const register = () => {
      navigator.serviceWorker
        .register("/sw.js", { updateViaCache: "none" })
        .then((reg) => {
          watch(reg);
          reg.update().catch(() => {});
          updateTimer = setInterval(() => reg.update().catch(() => {}), 60 * 60 * 1000);
        })
        .catch((error) => console.warn("Service worker registration failed", error));
      cacheShell();
      window.setTimeout(cacheShell, 6000);
    };

    if (document.readyState === "complete") register();
    else window.addEventListener("load", register, { once: true });

    return () => {
      window.removeEventListener("load", register);
      window.removeEventListener(LANG_EVENT, onLang);
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
      if (updateTimer) clearInterval(updateTimer);
    };
  }, []);

  if (!waiting) return null;
  const t = COPY[lang];

  return (
    <div className="app-update-toast" role="status" aria-label={t.aria}>
      <span>{t.msg}</span>
      <button type="button" onClick={() => waiting.postMessage("SKIP_WAITING")}>
        {t.action}
      </button>
    </div>
  );
}

"use client";

import { trackAnalytics } from "@/lib/analytics";
import type { Language } from "./types";

const TRANSLATOR_URL = "https://suvadityamuk-traduceme.hf.space/";
const TELEGRAM_URL = "https://t.me/TraducemeVzlaBot";

type TranslatorBannerCopy = {
  translatorTitle: string;
  translatorBody: string;
  translatorOpen: string;
  translatorTelegram: string;
};

export default function TranslatorBanner({
  language,
  copy,
}: {
  language: Language;
  copy: TranslatorBannerCopy;
}) {
  return (
    <aside
      className="translator-banner"
      role="complementary"
      aria-label={copy.translatorTitle}
      data-testid="translator-banner"
    >
      <span className="translator-banner-icon" aria-hidden="true">🌐</span>
      <div className="translator-banner-text">
        <b>{copy.translatorTitle}</b>
        <span>{copy.translatorBody}</span>
      </div>
      <div className="translator-banner-actions">
        <a
          className="translator-banner-link primary"
          href={TRANSLATOR_URL}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => trackAnalytics("translator_open", { surface: "banner", language })}
        >
          {copy.translatorOpen}
        </a>
        <a
          className="translator-banner-link"
          href={TELEGRAM_URL}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => trackAnalytics("translator_telegram", { surface: "banner", language })}
        >
          {copy.translatorTelegram}
        </a>
      </div>
    </aside>
  );
}

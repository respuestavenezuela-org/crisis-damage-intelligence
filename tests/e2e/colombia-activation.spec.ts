import { expect, test } from "@playwright/test";

const incidentId = "colombia-2026-08-10-san-jose-del-palmar";
const registryPath = `/data/incidents/${incidentId}.json`;

test("publishes a bounded, source-backed Colombia activation bulletin", async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/colombia");

  const main = page.getByRole("main");
  await expect(main).toHaveAttribute("data-incident-id", incidentId);
  await expect(main).toHaveAttribute("data-status", "activated-holding-bulletin");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/San José del Palmar/);
  await expect(page.getByText("7.4", { exact: true })).toBeVisible();
  await expect(page.getByText("20 km de San José del Palmar, Chocó", { exact: true })).toBeVisible();
  await expect(page.locator("dd").filter({ hasText: "96 km" })).toContainText("103 km");
  await expect(page.getByRole("heading", { name: "No existe amenaza de tsunami" })).toBeVisible();
  await expect(page.getByText(/No se publica aún una capa pública de daños/)).toBeVisible();
  await expect(page.getByText(/no significa ausencia de daños/)).toBeVisible();
  await expect(page.getByText(/18 réplicas registradas hasta las 12:00/)).toBeVisible();
  await expect(page.getByText(/no un balance oficial de daños de la UNGRD/)).toBeVisible();
  await expect(page.getByText(/posibles afectaciones en nueve municipios de Chocó/)).toBeVisible();
  await expect(page.getByText(/cuatro grupos USAR de Bogotá, Envigado, Yopal y Medellín/)).toBeVisible();

  const registryLink = page.getByRole("link", { name: /Registro JSON/ }).first();
  await expect(registryLink).toHaveAttribute("href", registryPath);

  const externalLinks = page.locator("a[target='_blank']");
  expect(await externalLinks.count()).toBeGreaterThanOrEqual(6);
  for (const link of await externalLinks.all()) {
    await expect(link).toHaveAttribute("href", /^https:\/\//);
    await expect(link).toHaveAttribute("rel", /noreferrer/);
    await expect(link).toHaveAttribute("rel", /noopener/);
  }

  const registryResponse = await request.get(registryPath);
  expect(registryResponse.ok()).toBe(true);
  const registry = await registryResponse.json();
  expect(registry).toMatchObject({
    schemaVersion: "1.0.0",
    incidentId,
    status: "activated-holding-bulletin",
    event: {
      magnitude: 7.4,
      depthKm: 96,
      depthContext: {
        officialAlternativeKm: 103,
        officialAlternativeSourceId: "sgc-technical-update",
      },
      sourceEventId: "202608101234",
      usgsEventId: "us6000tjl2",
    },
    tsunami: {
      status: "no-threat",
      actionsRequired: false,
    },
    publicDamageLayer: {
      status: "not-published",
    },
    privacy: {
      personalDataPublished: false,
      exactHouseholdLocationsPublished: false,
    },
  });
  expect(registry.sources.every((source: { url: string }) => source.url.startsWith("https://"))).toBe(true);
  expect(
    registry.sources.some(
      (source: { id: string; authority: string }) =>
        source.id === "ungrd-initial-response" && source.authority === "official-colombia",
    ),
  ).toBe(true);
  expect(
    registry.sources.some(
      (source: { id: string; authority: string }) =>
        source.id === "sgc-technical-update" && source.authority === "official-colombia",
    ),
  ).toBe(true);

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
});

test("supports keyboard entry and preserves the Venezuela incident", async ({ page }) => {
  await page.goto("/colombia");

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: /Saltar al contenido/ })).toBeFocused();
  await expect(page.getByRole("link", { name: /Venezuela · incidente preservado/ })).toHaveAttribute("href", "/");

  await page.goto("/");
  await expect(page.getByTestId("colombia-activation-link")).toHaveAttribute("href", "/colombia");

  await page.goto("/lite");
  await expect(page.getByTestId("lite-colombia-activation-link")).toHaveAttribute("href", "/colombia");
});

test("keeps the Colombia activation control usable across field breakpoints", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("respuesta-venezuela:first-visit-thanks-dismissed:v1", "1");
    window.localStorage.setItem("rv-install-dismissed-at", String(Date.now()));
  });

  for (const width of [360, 390, 430, 768]) {
    await page.setViewportSize({ width, height: width === 768 ? 1024 : 844 });
    await page.goto("/");

    const activation = page.getByTestId("colombia-activation-link");
    await expect(activation).toBeVisible();
    await expect(activation).toHaveAttribute("href", "/colombia");

    const layout = await page.evaluate(() => {
      const rect = (element: Element | null) => {
        if (!element) return null;
        const bounds = element.getBoundingClientRect();
        return {
          left: bounds.left,
          top: bounds.top,
          right: bounds.right,
          bottom: bounds.bottom,
          width: bounds.width,
          height: bounds.height,
        };
      };
      const activationRect = rect(document.querySelector('[data-testid="colombia-activation-link"]'));
      const aboutRect = rect(document.querySelector('[data-testid="mobile-about-toggle"]'));
      const languageRects = Array.from(
        document.querySelectorAll(".left-rail > .segmented button"),
        (button) => rect(button),
      ).filter((item): item is NonNullable<typeof item> => item !== null);

      return {
        activationRect,
        aboutRect,
        languageRects,
        horizontalOverflow:
          document.documentElement.scrollWidth > document.documentElement.clientWidth,
      };
    });

    expect(layout.horizontalOverflow).toBe(false);
    expect(layout.activationRect).not.toBeNull();
    expect(layout.activationRect?.height).toBeGreaterThanOrEqual(44);

    if (width <= 760) {
      expect(layout.activationRect?.width).toBeGreaterThanOrEqual(44);
      expect(layout.aboutRect?.height).toBeGreaterThanOrEqual(44);
      expect(layout.languageRects).toHaveLength(2);

      const controls = [
        layout.activationRect,
        layout.aboutRect,
        ...layout.languageRects,
      ].filter((item): item is NonNullable<typeof item> => item !== null);
      for (let index = 1; index < controls.length; index += 1) {
        expect(controls[index - 1].right).toBeLessThanOrEqual(controls[index].left);
      }
    } else {
      expect(layout.aboutRect).toBeNull();
    }
  }
});

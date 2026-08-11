import { expect, test } from "@playwright/test";

const incidentId = "colombia-2026-08-10-san-jose-del-palmar";
const registryPath = `/data/incidents/${incidentId}.json`;
const mappingPath = "/data/incidents/colombia-2026-08-10-emsr916-map.json";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("respuesta-venezuela:first-visit-thanks-dismissed:v1", "1");
    window.localStorage.setItem("rv-install-dismissed-at", String(Date.now()));
  });
});

test("publishes a map-first, source-backed Colombia operations view", async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/colombia");

  const main = page.getByRole("main");
  await expect(main).toHaveAttribute("data-incident-id", incidentId);
  await expect(main).toHaveAttribute("data-status", "activated-holding-bulletin");
  await expect(main).toHaveAttribute("data-map-activation", "EMSR916");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mapa operativo del sismo");

  const map = page.getByTestId("colombia-map-canvas");
  await expect(map).toBeVisible();
  await expect(map).toHaveAttribute("data-mode", "reference");
  await expect(map).toHaveAttribute("data-visible-aoi-count", "4");
  await expect(map).toHaveAttribute("data-before-ready", "false");
  await expect(map).toHaveAttribute("data-after-ready", "false");
  await expect(map).toHaveAttribute("data-selected-aoi", "");

  await expect(page.getByText("M7.4", { exact: true })).toBeVisible();
  await expect(page.getByText("96 km", { exact: true })).toBeVisible();
  await expect(page.getByText("Sin amenaza de tsunami", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Referencia visual · fecha de captura no verificada").first(),
  ).toBeVisible();
  await expect(page.getByText(/no son límites de daños/)).toBeVisible();

  await expect(page.getByRole("button", { name: "Antes", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Después", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Mapa", exact: true }).click();
  await expect(map).toHaveAttribute("data-mode", "map");
  await page.getByRole("button", { name: "Referencia", exact: true }).click();
  await expect(map).toHaveAttribute("data-mode", "reference");

  await page.getByTestId("colombia-aoi-03").click();
  await expect(map).toHaveAttribute("data-selected-aoi", "emsr916-aoi03");
  await expect(page.getByRole("heading", { name: "Centro de Cali" })).toBeVisible();
  await expect(page.getByText("Pleiades · VHR1", { exact: true })).toBeVisible();

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
      sourceEventId: "202608101234",
    },
    tsunami: {
      status: "no-threat",
      actionsRequired: false,
    },
    publicDamageLayer: {
      status: "not-published",
    },
    mapping: {
      activationCode: "EMSR916",
      status: "official-areas-published-imagery-waiting",
      mapSnapshot: mappingPath,
    },
  });
  expect(
    registry.sources.some(
      (source: { id: string; authority: string }) =>
        source.id === "copernicus-emsr916" && source.authority === "official-international",
    ),
  ).toBe(true);

  const mappingResponse = await request.get(mappingPath);
  expect(mappingResponse.ok()).toBe(true);
  const mapping = await mappingResponse.json();
  expect(mapping).toMatchObject({
    schemaVersion: "1.0.0",
    activationCode: "EMSR916",
    status: "open",
    imagery: {
      comparisonState: "scheduled",
      before: null,
      after: null,
      reference: {
        role: "visual-reference-only",
        source: "Esri World Imagery",
      },
    },
  });
  expect(mapping.aois).toHaveLength(4);
  expect(mapping.aois.every((aoi: { extentWkt: string }) => aoi.extentWkt.startsWith("POLYGON"))).toBe(
    true,
  );
  expect(
    mapping.aois.every(
      (aoi: { products: Array<{ status: string; images: Array<{ acquisitionUtc: string }> }> }) =>
        aoi.products[0]?.status === "waiting" &&
        aoi.products[0]?.images[0]?.acquisitionUtc.startsWith("2026-08-"),
    ),
  ).toBe(true);

  const layout = await page.evaluate(() => ({
    horizontalOverflow:
      document.documentElement.scrollWidth > document.documentElement.clientWidth,
    mapHeight:
      document.querySelector('[data-testid="colombia-map-canvas"]')?.getBoundingClientRect().height ??
      0,
  }));
  expect(layout.horizontalOverflow).toBe(false);
  expect(layout.mapHeight).toBeGreaterThanOrEqual(800);
});

test("supports keyboard entry, language switching, and compact source disclosure", async ({ page }) => {
  await page.goto("/colombia");

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Ir al mapa" })).toBeFocused();
  await expect(page.getByRole("link", { name: "Venezuela" })).toHaveAttribute("href", "/");

  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Earthquake operations map");
  await expect(page.getByRole("button", { name: "Before", exact: true })).toBeDisabled();
  await expect(page.getByText("No tsunami threat", { exact: true })).toBeVisible();

  await page.getByText("Sources and method", { exact: true }).click();
  const externalLinks = page.locator("a[target='_blank']");
  expect(await externalLinks.count()).toBeGreaterThanOrEqual(4);
  for (const link of await externalLinks.all()) {
    await expect(link).toHaveAttribute("href", /^https:\/\//);
    await expect(link).toHaveAttribute("rel", /noreferrer/);
    await expect(link).toHaveAttribute("rel", /noopener/);
  }
  await expect(page.getByRole("link", { name: "Event registry" })).toHaveAttribute(
    "href",
    registryPath,
  );
  await expect(page.getByRole("link", { name: "Map snapshot" })).toHaveAttribute(
    "href",
    mappingPath,
  );

  await page.goto("/");
  await expect(page.getByTestId("colombia-activation-link")).toHaveAttribute("href", "/colombia");
  await page.goto("/lite");
  await expect(page.getByTestId("lite-colombia-activation-link")).toHaveAttribute(
    "href",
    "/colombia",
  );
});

test("keeps the map and principal controls usable across field breakpoints", async ({ page }) => {
  for (const width of [360, 390, 430, 768, 1440]) {
    const height = width === 768 ? 1024 : width === 1440 ? 900 : 844;
    await page.setViewportSize({ width, height });
    await page.goto("/colombia");

    const map = page.getByTestId("colombia-map-canvas");
    await expect(map).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

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
      const principalControls = Array.from(
        document.querySelectorAll(
          "[class*='languageControl'] button, [class*='modeControl'] button, [data-testid^='colombia-aoi-']",
        ),
        (element) => rect(element),
      ).filter((item): item is NonNullable<typeof item> => item !== null);

      return {
        horizontalOverflow:
          document.documentElement.scrollWidth > document.documentElement.clientWidth,
        map: rect(document.querySelector('[data-testid="colombia-map-canvas"]')),
        rail: rect(document.querySelector("aside")),
        principalControls,
      };
    });

    expect(layout.horizontalOverflow).toBe(false);
    expect(layout.map?.width).toBeGreaterThanOrEqual(width - 1);
    expect(layout.map?.height).toBeGreaterThanOrEqual(height - 1);
    expect(layout.principalControls.length).toBeGreaterThanOrEqual(10);
    for (const control of layout.principalControls) {
      expect(control.height).toBeGreaterThanOrEqual(44);
      expect(control.width).toBeGreaterThanOrEqual(44);
    }

    if (width <= 760) {
      expect(layout.rail?.height).toBeLessThanOrEqual(height * 0.49);
      expect(layout.rail?.bottom).toBeLessThanOrEqual(height);
    } else {
      expect(layout.rail?.width).toBeGreaterThanOrEqual(360);
      expect(layout.rail?.height).toBeGreaterThanOrEqual(height - 30);
    }
  }
});

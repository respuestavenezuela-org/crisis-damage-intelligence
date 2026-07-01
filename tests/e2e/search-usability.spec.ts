import { expect, test, type Locator, type Page } from "@playwright/test";
import {
  DEFAULT_AOI_ID,
  DEFAULT_CITY_LABEL,
  DEFAULT_PRIORITY_FEATURE_ID,
  expectMobileDockUsable,
  focusedMapState,
  globalSearchInput,
  globalSearchOptions,
  globalSearchResults,
  keepMapRastersLight,
  openInspector,
  priorityRows,
} from "./helpers/crisis-map";

// These tests intercept data and tile requests. Block service workers so
// Playwright routes see the same network requests every run.
test.use({ serviceWorkers: "block" });

const searchViewports = [
  { width: 360, height: 740 },
  { width: 390, height: 844 },
  { width: 430, height: 932 },
  { width: 768, height: 1024 },
];

async function loadMap(page: Page, viewport = { width: 390, height: 844 }) {
  await keepMapRastersLight(page);
  await page.setViewportSize(viewport);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Respuesta Venezuela" })).toBeVisible();
  await expect(page.getByRole("region", { name: /Mapa operacional de/i })).toBeVisible();
}

async function searchFor(page: Page, query: string) {
  const input = globalSearchInput(page);
  await expect(input).toBeVisible();
  await input.fill(query);
  await expect(input).toHaveValue(query);
  await expect(globalSearchResults(page)).toBeVisible();
  return globalSearchOptions(page);
}

async function optionFor(page: Page, text: string | RegExp) {
  const option = globalSearchOptions(page).filter({ hasText: text }).first();
  await expect(option).toBeVisible();
  return option;
}

for (const viewport of searchViewports) {
  test(`search is visible and finds operational records at ${viewport.width}px`, async ({ page }) => {
    await loadMap(page, viewport);

    const input = globalSearchInput(page);
    await expect(input).toBeVisible();
    await expect(input).toBeInViewport({ ratio: 0.95 });
    const box = await input.boundingBox();
    expect(box?.height).toBeGreaterThanOrEqual(40);
    expect(box?.width).toBeGreaterThanOrEqual(Math.min(260, viewport.width - 32));

    await searchFor(page, "La Guaira");
    await optionFor(page, DEFAULT_CITY_LABEL);

    await searchFor(page, DEFAULT_AOI_ID);
    await optionFor(page, DEFAULT_AOI_ID);

    await searchFor(page, DEFAULT_PRIORITY_FEATURE_ID);
    await optionFor(page, DEFAULT_PRIORITY_FEATURE_ID);
  });
}

test("selecting a feature search result focuses the map without breaking the mobile dock", async ({ page }) => {
  await loadMap(page, { width: 390, height: 844 });

  await searchFor(page, DEFAULT_PRIORITY_FEATURE_ID);
  await (await optionFor(page, DEFAULT_PRIORITY_FEATURE_ID)).click();

  await expect(globalSearchResults(page)).toBeHidden();
  await expect(page.locator(".map-node")).toHaveAttribute("data-focused-id", DEFAULT_PRIORITY_FEATURE_ID);
  await expect(page.locator(".map-node")).toHaveAttribute("data-map-zoom", "18");
  await expect(page.locator(".ol-popup")).toBeVisible();
  await expectMobileDockUsable(page);
  await expect(page.getByTestId("mobile-inspector-toggle")).toContainText(DEFAULT_PRIORITY_FEATURE_ID);

  const state = await focusedMapState(page);
  expect(state.center).toMatch(/^10\.\d+,-67\.\d+$/);
});

test("priority evidence exposes useful coordinate copy and Google Maps actions", async ({ page }) => {
  await page.addInitScript(() => {
    let text = "";
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        readText: async () => text,
        writeText: async (nextText: string) => {
          text = nextText;
        },
      },
    });
  });
  await loadMap(page, { width: 768, height: 1024 });

  const inspector = await openInspector(page);
  const firstPriority = priorityRows(inspector).first();
  await expect(firstPriority).toBeVisible();
  await firstPriority.click();

  const evidencePanel = page.locator(".evidence-panel");
  await expect(evidencePanel).toBeVisible();
  const mapsLink = evidencePanel.getByRole("link", { name: /Google Maps/i });
  await expect(mapsLink).toBeVisible();
  await expect(mapsLink).toHaveAttribute("href", /^https:\/\/www\.google\.com\/maps\/search\/\?api=1&query=10\.\d+,-67\.\d+$/);

  const copyButton = page
    .getByTestId("copy-coordinates")
    .or(evidencePanel.getByRole("button", { name: /copiar coordenadas|copy coordinates/i }))
    .first();
  await expect(copyButton).toBeVisible();
  await copyButton.click();

  const copiedCoordinates = await page.evaluate(() => navigator.clipboard.readText());
  expect(copiedCoordinates).toMatch(/^10\.\d+,\s*-67\.\d+$/);
});

test("priority action coordinates match the focused map point when EMS centroids are outside multipolygons", async ({ page }) => {
  await page.addInitScript(() => {
    let text = "";
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        readText: async () => text,
        writeText: async (nextText: string) => {
          text = nextText;
        },
      },
    });
  });
  await loadMap(page, { width: 768, height: 1024 });

  const inspector = await openInspector(page);
  const row = inspector.getByTestId("priority-ems_00115");
  await row.scrollIntoViewIfNeeded();
  await expect(row).toBeVisible();
  await row.click();

  const state = await focusedMapState(page);
  expect(state.focusedId).toBe("ems_00115");
  expect(state.zoom).toBe("18");
  const focusedPoint = parseLatLon(state.center);

  const evidencePanel = page.locator(".evidence-panel");
  const mapsLink = evidencePanel.getByRole("link", { name: /Google Maps/i });
  const mapsPoint = parseLatLon(new URL((await mapsLink.getAttribute("href")) ?? "").searchParams.get("query"));
  expect(mapsPoint.lat).toBeCloseTo(focusedPoint.lat, 6);
  expect(mapsPoint.lon).toBeCloseTo(focusedPoint.lon, 6);

  await page.getByTestId("copy-coordinates").click();
  const copiedPoint = parseLatLon(await page.evaluate(() => navigator.clipboard.readText()));
  expect(copiedPoint.lat).toBeCloseTo(focusedPoint.lat, 6);
  expect(copiedPoint.lon).toBeCloseTo(focusedPoint.lon, 6);
});

test("priority sort chips keep the default order until an operator selects a sort", async ({ page }) => {
  await loadMap(page, { width: 768, height: 1024 });

  const inspector = await openInspector(page);
  const rows = priorityRows(inspector);
  await expect(rows.first()).toBeVisible();
  const initialOrder = await readPriorityIds(rows);

  const sortGroup = page.getByTestId("priority-sort");
  await expect(sortGroup).toBeVisible();
  const defaultSort = page.getByTestId("priority-sort-response-value");
  const sourceSort = page.getByTestId("priority-sort-source");
  await expect(defaultSort).toHaveAttribute("aria-pressed", "true");
  await expect(sourceSort).toHaveAttribute("aria-pressed", "false");

  await sourceSort.focus();
  await sourceSort.hover();
  expect(await readPriorityIds(rows)).toEqual(initialOrder);

  await sourceSort.click();
  await expect(sourceSort).toHaveAttribute("aria-pressed", "true");
  await expect
    .poll(async () => readPriorityIds(rows))
    .not.toEqual(initialOrder);
});

test("priority list exposes more than the first twelve high-priority candidates", async ({ page }) => {
  await loadMap(page, { width: 768, height: 1024 });

  const inspector = await openInspector(page);
  const rows = priorityRows(inspector);
  await expect(rows.first()).toBeVisible();
  await expect.poll(async () => rows.count()).toBeGreaterThan(12);
});

test("keyboard search supports Escape and a sane Tab path", async ({ page }) => {
  await loadMap(page, { width: 390, height: 844 });

  const input = globalSearchInput(page);
  await input.focus();
  await expect(input).toBeFocused();
  await page.keyboard.type("La Guaira");
  await expect(globalSearchResults(page)).toBeVisible();
  await expect(globalSearchOptions(page).first()).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(globalSearchResults(page)).toBeHidden();

  await page.keyboard.press("Tab");
  const activeElement = await page.evaluate(() => ({
    tagName: document.activeElement?.tagName ?? "",
    testId: document.activeElement?.getAttribute("data-testid") ?? "",
    role: document.activeElement?.getAttribute("role") ?? "",
  }));
  expect(activeElement.tagName).toMatch(/^(A|BUTTON|INPUT)$/);
  expect(activeElement.testId).not.toMatch(/^search-result-/);
  expect(activeElement.role).not.toBe("option");
});

async function readPriorityIds(rows: Locator) {
  return rows.evaluateAll((nodes) =>
    nodes.slice(0, 6).map((node) => node.querySelector("b")?.textContent?.trim() ?? node.textContent?.trim() ?? ""),
  );
}

function parseLatLon(value: string | null) {
  const [lat, lon] = (value ?? "").split(",").map((part) => Number(part.trim()));
  expect(Number.isFinite(lat)).toBe(true);
  expect(Number.isFinite(lon)).toBe(true);
  return { lat, lon };
}

import { Buffer } from "node:buffer";
import { expect, type Locator, type Page } from "@playwright/test";

export const DEFAULT_AOI_ID = "emsr884-aoi12-caraballeda";
export const DEFAULT_CITY_LABEL = /La Guaira|Caraballeda|Catia La Mar/i;
export const DEFAULT_PRIORITY_FEATURE_ID = "ems_00003";

export const transparentPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lI2NnQAAAABJRU5ErkJggg==",
  "base64",
);

export async function keepMapRastersLight(page: Page) {
  await page.route("**/data/tiles/**", (route) => {
    route.fulfill({ status: 200, contentType: "image/png", body: transparentPng });
  });
  await page.route("**/data/chips/**", (route) => {
    route.fulfill({ status: 200, contentType: "image/png", body: transparentPng });
  });
  await page.route("**/*.tif", (route) => route.abort("blockedbyclient"));
  await page.route("**/*.tiff", (route) => route.abort("blockedbyclient"));
  await page.route("https://server.arcgisonline.com/**", (route) => {
    route.fulfill({ status: 200, contentType: "image/png", body: transparentPng });
  });
  await page.route("https://tile.openstreetmap.org/**", (route) => {
    route.fulfill({ status: 200, contentType: "image/png", body: transparentPng });
  });
  await page.route("https://*.tile.openstreetmap.org/**", (route) => {
    route.fulfill({ status: 200, contentType: "image/png", body: transparentPng });
  });
  await page.route("https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/**", (route) => route.abort("blockedbyclient"));
  await page.route("https://sentinel-cogs.s3.us-west-2.amazonaws.com/**", (route) => route.abort("blockedbyclient"));
  await page.route("https://vantor-opendata.s3.amazonaws.com/**", (route) => route.abort("blockedbyclient"));
}

export async function expectActiveDownloadReachable(scope: Page | Locator) {
  const download = scope.getByRole("link", { name: "CSV" }).first();
  await download.scrollIntoViewIfNeeded();
  await expect(download).toBeVisible();
  await expect(download).toBeInViewport({ ratio: 0.5 });
  await expect(download).toHaveAttribute("href", new RegExp(`/data/aoi/${DEFAULT_AOI_ID}/`));
  const box = await download.boundingBox();
  expect(box?.height).toBeGreaterThanOrEqual(38);
}

export async function openMobileSheet(page: Page, toggleTestId: string, sheetTestId: string) {
  await page.getByTestId(toggleTestId).click();
  const sheet = page.getByTestId(sheetTestId);
  await expect(sheet).toBeVisible();
  return sheet;
}

export async function closeSheet(sheet: Locator) {
  await sheet.getByRole("button", { name: "Cerrar" }).click();
  await expect(sheet).toBeHidden();
}

export function priorityRows(scope: Page | Locator) {
  return scope.locator(".priority-row");
}

export async function openInspector(page: Page) {
  const mobileToggle = page.getByTestId("mobile-inspector-toggle");
  if (await mobileToggle.isVisible()) {
    await mobileToggle.click();
    const sheet = page.getByTestId("mobile-inspector-sheet");
    await expect(sheet).toBeVisible();
    return sheet;
  }
  const rail = page.getByTestId("right-rail");
  await expect(rail).toBeVisible();
  return rail;
}

export function globalSearchInput(page: Page) {
  return page.getByTestId("global-search-input");
}

export function globalSearchResults(page: Page) {
  return page.getByTestId("global-search-results");
}

export function globalSearchOptions(page: Page) {
  return page.locator('[data-testid^="search-result-"], [role="option"]');
}

export async function expectMobileDockUsable(page: Page) {
  await expect(page.getByTestId("right-rail")).toBeVisible();
  await expect(page.getByTestId("mobile-zona-toggle")).toBeVisible();
  await expect(page.getByTestId("mobile-capas-toggle")).toBeVisible();
  await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
}

export async function focusedMapState(page: Page) {
  const map = page.locator(".map-node");
  await expect(map).toBeVisible();
  return {
    focusedId: await map.getAttribute("data-focused-id"),
    center: await map.getAttribute("data-map-center"),
    zoom: await map.getAttribute("data-map-zoom"),
  };
}

import { Buffer } from "node:buffer";
import { expect, type Page, test } from "@playwright/test";

const transparentPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lI2NnQAAAABJRU5ErkJggg==",
  "base64",
);

async function keepMapRastersLight(page: Page) {
  await page.route("**/data/tiles/**", (route) => {
    route.fulfill({ status: 200, contentType: "image/png", body: transparentPng });
  });
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

async function expectActiveDownloadReachable(page: Page) {
  const download = page.getByRole("link", { name: "CSV" }).first();
  await download.scrollIntoViewIfNeeded();
  await expect(download).toBeVisible();
  await expect(download).toBeInViewport({ ratio: 0.5 });
  await expect(download).toHaveAttribute("href", /\/data\/aoi\/emsr884-aoi12-caraballeda\//);
  const box = await download.boundingBox();
  expect(box?.height).toBeGreaterThanOrEqual(38);
}

test("mobile critical AOI workflow stays usable", async ({ page }) => {
  await keepMapRastersLight(page);
  const loadedDataUrls: string[] = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/data/aoi/") && (url.endsWith(".geojson") || url.endsWith(".jsonl"))) {
      loadedDataUrls.push(url);
    }
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Respuesta Venezuela" })).toBeVisible();
  await expect(page.getByTestId("city-la-guaira")).toBeVisible();
  await expect(page.getByRole("link", { name: "CSV" }).first()).toBeVisible();

  await expect.poll(() => loadedDataUrls.some((url) => url.includes("emsr884-aoi12-caraballeda"))).toBe(true);
  expect(loadedDataUrls.some((url) => url.includes("emsr884-aoi06-moron"))).toBe(false);
  expect(loadedDataUrls.some((url) => url.includes("external-msft-catia-la-mar-predicted-damage"))).toBe(false);

  const toolbarBox = await page.getByTestId("map-toolbar").boundingBox();
  expect(toolbarBox?.height).toBeLessThanOrEqual(60);
  const mobileSheet = page.getByTestId("mobile-inspector-sheet");
  await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
  await expect(page.getByTestId("mobile-inspector-toggle")).toContainText("12 filas de prioridad listas");
  await page.getByTestId("mobile-inspector-toggle").click();
  await expect(mobileSheet).toBeVisible();
  await expect(page.getByRole("heading", { name: "Brief operativo" })).toBeVisible();
  await expect(mobileSheet).toContainText("12 filas de prioridad listas");
  await mobileSheet.getByRole("button", { name: "Cerrar" }).click();
  await expect(mobileSheet).toBeHidden();
  await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
  await page.getByTestId("mobile-inspector-toggle").click();
  await expect(mobileSheet).toBeVisible();
  await mobileSheet.getByRole("button", { name: "Cerrar" }).click();
  await expect(mobileSheet).toBeHidden();

  await page.getByTestId("map-controls-toggle").click();
  await expect(page.getByTestId("filter-severe")).toBeVisible();

  await page.getByTestId("filter-severe").click();
  await expect(page.getByTestId("filter-severe")).toHaveAttribute("aria-pressed", "true");

  const beforeButton = page.getByTestId("mode-before");
  if (await beforeButton.isEnabled()) {
    await beforeButton.click();
    await expect(beforeButton).toHaveAttribute("aria-pressed", "true");
  }
  await page.getByTestId("mode-after").click();
  await expect(page.getByTestId("mode-after")).toHaveAttribute("aria-pressed", "true");
  await page.getByTestId("map-controls-toggle").click();

  await page.getByTestId("mobile-inspector-toggle").click();
  await expect(mobileSheet).toBeVisible();
  await mobileSheet.getByRole("button", { name: "Ver prioridad" }).click();
  const firstPriority = mobileSheet.locator('[data-testid^="priority-"]').first();
  await expect(firstPriority).toBeVisible();
  await firstPriority.click();
  await expect(page.locator(".map-node")).toHaveAttribute("data-map-zoom", "18");
  await expect(page.locator(".ol-popup")).toBeVisible();
  await expect(page.getByTestId("mobile-inspector-sheet")).toBeHidden();
  await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
  await expect(page.getByTestId("mobile-inspector-toggle")).toContainText("Abrir");
});

for (const viewport of [
  { width: 360, height: 740, mobileSheet: true },
  { width: 430, height: 932, mobileSheet: true },
  { width: 768, height: 1024, mobileSheet: false },
]) {
  test(`low-bandwidth essentials remain reachable at ${viewport.width}px`, async ({ page }) => {
    await keepMapRastersLight(page);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Respuesta Venezuela" })).toBeVisible();
    await expect(page.getByTestId("city-la-guaira")).toBeVisible();
    await expect(page.getByTestId("city-la-guaira")).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("region", { name: /Mapa operacional de/i })).toBeVisible();
    await expect(page.getByTestId("map-toolbar")).toBeVisible();
    await expectActiveDownloadReachable(page);

    const activeAoiBox = await page.getByTestId("city-la-guaira").boundingBox();
    expect(activeAoiBox?.height).toBeGreaterThanOrEqual(44);

    if (viewport.mobileSheet) {
      const toolbarBox = await page.getByTestId("map-toolbar").boundingBox();
      expect(toolbarBox?.height).toBeLessThanOrEqual(60);
      await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
      await page.getByTestId("mobile-inspector-toggle").click();
      await expect(page.getByTestId("mobile-inspector-sheet")).toBeVisible();
      await expect(page.getByTestId("mobile-inspector-sheet")).toContainText("Brief operativo");
      await expect(page.getByTestId("mobile-inspector-sheet")).toContainText("Con enlace débil");
      await page.getByTestId("mobile-inspector-sheet").getByRole("button", { name: "Cerrar" }).click();
      await expect(page.getByTestId("mobile-inspector-sheet")).toBeHidden();
      await page.getByTestId("map-controls-toggle").click();
      await expect(page.getByTestId("filter-severe")).toBeVisible();
    } else {
      await expect(page.getByTestId("mobile-inspector-sheet")).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Brief operativo" })).toBeVisible();
      await expect(page.getByTestId("filter-severe")).toBeVisible();
    }
  });
}

test("mobile shell keeps downloads and AOI metadata visible when active damage and VLM fail", async ({ page }) => {
  await keepMapRastersLight(page);
  await page.setViewportSize({ width: 360, height: 740 });
  await page.route("**/data/aoi/emsr884-aoi12-caraballeda/damage.geojson", (route) => {
    route.fulfill({
      status: 404,
      contentType: "text/plain",
      body: "simulated missing active damage layer",
    });
  });
  await page.route("**/data/aoi/emsr884-aoi12-caraballeda/vlm_before_after_review.jsonl", (route) => {
    route.fulfill({
      status: 503,
      contentType: "text/plain",
      body: "simulated unavailable active VLM layer",
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Respuesta Venezuela" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("No se pudo cargar la geometría de daños.");
  await expect(page.getByRole("status")).toContainText("No se pudo cargar evidencia VLM.");
  await expect(page.getByTestId("city-la-guaira")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("city-moron")).toBeVisible();
  await expectActiveDownloadReachable(page);

  const mobileSheet = page.getByTestId("mobile-inspector-sheet");
  await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
  await page.getByTestId("mobile-inspector-toggle").click();
  await expect(mobileSheet).toBeVisible();
  await expect(mobileSheet).toContainText("Brief operativo");
  await expect(mobileSheet).toContainText("Datos operativos EMSR884");
  await expect(mobileSheet).toContainText("Con enlace débil");
  await expect(mobileSheet).toContainText("No se pudo cargar la geometría de daños.");
});

import { expect, test } from "@playwright/test";
import {
  closeSheet,
  expectActiveDownloadReachable,
  keepMapRastersLight,
  openMobileSheet,
} from "./helpers/crisis-map";

// These smoke tests intercept data and tile requests. Block service workers so
// Playwright routes see the same network requests every run.
test.use({ serviceWorkers: "block" });

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
  await expect(page.getByTestId("mobile-zona-toggle")).toContainText("La Guaira");

  const zoneSheet = await openMobileSheet(page, "mobile-zona-toggle", "mobile-zona-sheet");
  await expect(zoneSheet.getByTestId("city-la-guaira")).toBeVisible();
  await expect(zoneSheet.getByTestId("city-la-guaira")).toHaveAttribute("aria-pressed", "true");
  await closeSheet(zoneSheet);

  const aboutSheet = await openMobileSheet(page, "mobile-about-toggle", "mobile-about-sheet");
  await expectActiveDownloadReachable(aboutSheet);
  await closeSheet(aboutSheet);

  await expect.poll(() => loadedDataUrls.some((url) => url.includes("emsr884-aoi12-caraballeda"))).toBe(true);
  expect(loadedDataUrls.some((url) => url.includes("emsr884-aoi06-moron"))).toBe(false);
  expect(loadedDataUrls.some((url) => url.includes("external-msft-catia-la-mar-predicted-damage"))).toBe(false);

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

  const layersSheet = await openMobileSheet(page, "mobile-capas-toggle", "mobile-capas-sheet");
  await expect(layersSheet.getByTestId("filter-severe")).toBeVisible();

  await layersSheet.getByTestId("filter-severe").click();
  await expect(layersSheet.getByTestId("filter-severe")).toHaveAttribute("aria-pressed", "true");

  const beforeButton = layersSheet.getByTestId("mode-before");
  if (await beforeButton.isEnabled()) {
    await beforeButton.click();
    await expect(beforeButton).toHaveAttribute("aria-pressed", "true");
  }
  await layersSheet.getByTestId("mode-after").click();
  await expect(layersSheet.getByTestId("mode-after")).toHaveAttribute("aria-pressed", "true");
  await closeSheet(layersSheet);

  await page.getByTestId("mobile-inspector-toggle").click();
  await expect(mobileSheet).toBeVisible();
  await mobileSheet.getByRole("button", { name: "Ver prioridad" }).click();
  const firstPriority = mobileSheet.locator(".priority-row").first();
  await expect(firstPriority).toBeVisible();
  await firstPriority.click();
  await expect(page.locator(".map-node")).toHaveAttribute("data-map-zoom", "18");
  await expect(page.locator(".ol-popup")).toBeVisible();
  await expect(page.getByTestId("mobile-inspector-sheet")).toBeHidden();
  await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
  await expect(page.getByTestId("mobile-inspector-toggle")).toContainText(/ems_\d+/);
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
    await expect(page.getByRole("region", { name: /Mapa operacional de/i })).toBeVisible();

    if (viewport.mobileSheet) {
      await expect(page.getByTestId("mobile-zona-toggle")).toContainText("La Guaira");
      const zoneSheet = await openMobileSheet(page, "mobile-zona-toggle", "mobile-zona-sheet");
      await expect(zoneSheet.getByTestId("city-la-guaira")).toBeVisible();
      await expect(zoneSheet.getByTestId("city-la-guaira")).toHaveAttribute("aria-pressed", "true");
      const activeAoiBox = await zoneSheet.getByTestId("city-la-guaira").boundingBox();
      expect(activeAoiBox?.height).toBeGreaterThanOrEqual(44);
      await closeSheet(zoneSheet);

      const aboutSheet = await openMobileSheet(page, "mobile-about-toggle", "mobile-about-sheet");
      await expectActiveDownloadReachable(aboutSheet);
      await closeSheet(aboutSheet);

      await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
      await page.getByTestId("mobile-inspector-toggle").click();
      await expect(page.getByTestId("mobile-inspector-sheet")).toBeVisible();
      await expect(page.getByTestId("mobile-inspector-sheet")).toContainText("Brief operativo");
      await expect(page.getByTestId("mobile-inspector-sheet")).toContainText("Con enlace débil");
      await page.getByTestId("mobile-inspector-sheet").getByRole("button", { name: "Cerrar" }).click();
      await expect(page.getByTestId("mobile-inspector-sheet")).toBeHidden();

      const layersSheet = await openMobileSheet(page, "mobile-capas-toggle", "mobile-capas-sheet");
      await expect(layersSheet.getByTestId("filter-severe")).toBeVisible();
      await closeSheet(layersSheet);
    } else {
      await expect(page.getByTestId("city-la-guaira")).toBeVisible();
      await expect(page.getByTestId("city-la-guaira")).toHaveAttribute("aria-pressed", "true");
      const activeAoiBox = await page.getByTestId("city-la-guaira").boundingBox();
      expect(activeAoiBox?.height).toBeGreaterThanOrEqual(44);
      await expect(page.getByTestId("map-toolbar")).toBeVisible();
      await expectActiveDownloadReachable(page);
      await expect(page.getByTestId("mobile-inspector-sheet")).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Brief operativo" })).toBeVisible();
      await expect(page.getByTestId("filter-severe")).toBeVisible();
    }
  });
}

test("mobile shell keeps downloads and AOI metadata visible when active damage and VLM fail", async ({ page }) => {
  await keepMapRastersLight(page);
  await page.setViewportSize({ width: 360, height: 740 });
  await page.route("**/data/aoi/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/data/aoi/emsr884-aoi12-caraballeda/damage.geojson") {
      await route.fulfill({
        status: 404,
        contentType: "text/plain",
        body: "simulated missing active damage layer",
      });
      return;
    }
    if (pathname === "/data/aoi/emsr884-aoi12-caraballeda/vlm_before_after_review.jsonl") {
      await route.fulfill({
        status: 503,
        contentType: "text/plain",
        body: "simulated unavailable active VLM layer",
      });
      return;
    }
    await route.continue();
  });

  await page.goto("/");

  await expect(page.getByTestId("mobile-zona-toggle")).toBeVisible();
  const dataStatus = page.locator(".data-status");
  await expect(dataStatus).toContainText("No se pudo cargar la geometría de daños.");
  await expect(dataStatus).toContainText("No se pudo cargar evidencia VLM.");

  const zoneSheet = await openMobileSheet(page, "mobile-zona-toggle", "mobile-zona-sheet");
  await expect(zoneSheet.getByTestId("city-la-guaira")).toHaveAttribute("aria-pressed", "true");
  await expect(zoneSheet.getByTestId("city-moron")).toBeVisible();
  await closeSheet(zoneSheet);

  const aboutSheet = await openMobileSheet(page, "mobile-about-toggle", "mobile-about-sheet");
  await expectActiveDownloadReachable(aboutSheet);
  await closeSheet(aboutSheet);

  const mobileSheet = page.getByTestId("mobile-inspector-sheet");
  await expect(page.getByTestId("mobile-inspector-toggle")).toBeVisible();
  await page.getByTestId("mobile-inspector-toggle").click();
  await expect(mobileSheet).toBeVisible();
  await expect(mobileSheet).toContainText("Brief operativo");
  await expect(mobileSheet).toContainText("Datos operativos EMSR884");
  await expect(mobileSheet).toContainText("Con enlace débil");
  await expect(mobileSheet).toContainText("No se pudo cargar la geometría de daños.");
});

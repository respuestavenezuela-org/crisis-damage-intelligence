import { expect, test } from "@playwright/test";

test.describe("public aftermath reconstruction", () => {
  test("explains the first 72 hours and preserves source traceability", async ({ page }) => {
    const loadedHeavyData: string[] = [];
    page.on("request", (request) => {
      const url = request.url();
      if (/\/data\/(?:aoi|tiles)\//.test(url) || /\.(?:geojson|jsonl|pmtiles|tif)$/i.test(url)) {
        loadedHeavyData.push(url);
      }
    });

    await page.goto("/timeline");

    await expect(page.getByRole("heading", { name: "Lo que pasó después" })).toBeVisible();
    await expect(page.getByText("¿Cuándo llegó la ayuda — y cuándo llegó realmente a los sitios?")).toBeVisible();
    await expect(page.getByText(/La ayuda se movilizó pronto/)).toBeVisible();
    await expect(page.getByText("Observado en sitio").first()).toBeVisible();
    await expect(page.getByRole("img", { name: /Comparación antes y después/ }).first()).toBeVisible();

    const sourceLinks = page.locator('a[target="_blank"]');
    await expect(sourceLinks.first()).toHaveAttribute("href", /^https:\/\//);
    expect(loadedHeavyData).toEqual([]);

    await page.getByRole("button", { name: "Después de 72 h" }).click();
    await expect(page.getByRole("button", { name: "Después de 72 h" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator('article[id^="event-"]')).toHaveCount(10);

    await page.getByRole("button", { name: "EN", exact: true }).click();
    await expect(page.getByRole("heading", { name: "What happened after" })).toBeVisible();
    await expect(page.getByText("Not observed ≠ did not happen")).toBeVisible();
  });

  test("has no horizontal overflow on a small phone", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/timeline");

    await expect(page.getByRole("heading", { name: "Lo que pasó después" })).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1);

    const mapLink = page.getByRole("link", { name: "Abrir mapa de daños" });
    const box = await mapLink.boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  });

  test("is discoverable from lite view", async ({ page }) => {
    await page.goto("/lite");
    await expect(page.getByRole("link", { name: "Cronología" })).toHaveAttribute("href", "/timeline");
  });

  test("switches to the Morón evidence packet without loading map data", async ({ page }) => {
    const loadedHeavyData: string[] = [];
    page.on("request", (request) => {
      const url = request.url();
      if (/\/data\/(?:aoi|tiles)\//.test(url) || /\.(?:geojson|jsonl|pmtiles|tif)$/i.test(url)) {
        loadedHeavyData.push(url);
      }
    });

    await page.goto("/timeline/moron");

    await expect(page.getByRole("link", { name: /Morón y municipio Juan José Mora/ })).toHaveAttribute("aria-current", "page");
    await expect(page.getByText("Morón y municipio Juan José Mora, Carabobo").last()).toBeVisible();
    await expect(page.getByText(/su respuesta en Morón y municipio Juan José Mora/)).toBeVisible();
    await expect(page.getByText(/El daño fue cartografiado dentro de las primeras 24 horas/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Copernicus adquiere imagen postevento de Morón" })).toBeVisible();
    await expect(page.getByRole("img", { name: /elemento destruido en Morón/ }).first()).toBeVisible();
    await expect(page.getByText("Maquinaria pesada: hora de llegada no resuelta")).toBeVisible();
    expect(loadedHeavyData).toEqual([]);

    await page.getByRole("button", { name: "EN", exact: true }).click();
    await expect(page.getByText("Heavy machinery: arrival time unresolved")).toBeVisible();
  });
});

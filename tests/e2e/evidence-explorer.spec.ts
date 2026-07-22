import { expect, test } from "@playwright/test";

test.describe("full-pilot evidence explorer", () => {
  test("leads with findings, then exposes all 399 candidates without eager-loading detail imagery", async ({ page }) => {
    const evidenceImages: string[] = [];
    const observationIndexes: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("/data/chips/full-pilot-response-evidence/")) {
        evidenceImages.push(request.url());
      }
      if (request.url().endsWith("/full-pilot-response-evidence.jsonl")) {
        observationIndexes.push(request.url());
      }
    });

    await page.goto("/evidence/la-guaira");

    await expect(
      page.getByRole("heading", { name: "Qué muestran las imágenes" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Lo que la evidencia permite sostener" }),
    ).toBeVisible();
    expect(observationIndexes).toEqual([]);
    expect(evidenceImages).toEqual([]);

    await page.getByRole("tab", { name: "Explorar 399" }).click();
    await expect(
      page.getByRole("heading", { name: "399 resultados" }),
    ).toBeVisible();
    await expect(page.locator("button").filter({ hasText: "pilot_" })).toHaveCount(24);
    expect(observationIndexes).toHaveLength(1);
    expect(evidenceImages).toEqual([]);

    await page.getByRole("button", { name: "Mostrar filtros" }).click();
    await page.getByRole("button", { name: "Maquinaria", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "75 resultados" }),
    ).toBeVisible();

    const firstCandidate = page.locator("button").filter({ hasText: "pilot_" }).first();
    await firstCandidate.click();
    await expect(page.locator("#selected-cell-title")).toBeVisible();
    await expect(page).toHaveURL(/\?cell=pilot_r\d{3}_c\d{3}$/);
    await expect(page.locator("aside img").first()).toBeVisible();
    await expect.poll(() => evidenceImages.length).toBeGreaterThan(0);
    await expect(page.getByText("7 comparaciones publicadas")).toBeVisible();
    await expect(page.getByText("Par 1/7")).toBeVisible();
    await expect(page.getByText("Ambos modelos positivos")).toBeVisible();
    await expect(page.getByText(/AI triage|Triage automatizado/).first()).toBeVisible();
  });

  test("keeps reviewed highlights distinct from the complete candidate inventory", async ({ page }) => {
    await page.goto("/evidence/la-guaira");

    await page.getByRole("tab", { name: "Casos revisados" }).click();
    await expect(
      page.getByText(/no el universo completo/),
    ).toBeVisible();
    await expect(
      page.locator("#highlights-panel article").filter({ has: page.locator("figure") }),
    ).toHaveCount(10);

    await page.getByRole("tab", { name: "Hallazgos" }).click();
    await expect(
      page.getByText(/279 lo hicieron entre 24 y 48 horas/),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "Primera señal visible en imágenes disponibles",
      }),
    ).toBeVisible();
  });

  test("publishes mapped response sites without unstable visual unit counts", async ({ page }) => {
    const sourceImages: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("maps.mapaction.org") && /\.(jpg|png|pdf)$/i.test(request.url())) {
        sourceImages.push(request.url());
      }
    });

    await page.goto("/evidence/la-guaira");

    await expect(
      page.getByRole("heading", { name: "Dónde funcionó la respuesta" }),
    ).toBeVisible();
    await expect(page.locator("article").filter({ hasText: "Campamento Transitorio" })).toHaveCount(4);
    await expect(
      page.getByRole("heading", { name: "Campo de Golf de Caraballeda" }),
    ).toBeVisible();
    await expect(page.getByText("3.260", { exact: true })).toBeVisible();
    await expect(page.getByText("14", { exact: true }).first()).toBeVisible();
    await expect(
      page.getByText(/No publicamos conteos visuales de carpas/),
    ).toBeVisible();
    await expect(
      page.getByText(/MiniMax y Qwen produjeron rangos incompatibles/),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Abrir mapa fuente/ }),
    ).toHaveCount(5);
    expect(sourceImages).toEqual([]);
  });

  test("keeps the core atlas usable when the documentary expansion is unavailable", async ({ page }) => {
    await page.route("**/mapaction-response-sites-la-guaira.json", (route) =>
      route.fulfill({ status: 503, body: "temporarily unavailable" }),
    );

    await page.goto("/evidence/la-guaira");

    await expect(
      page.getByRole("heading", { name: "Lo que la evidencia permite sostener" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Dónde funcionó la respuesta" }),
    ).toHaveCount(0);
    await page.getByRole("tab", { name: "Explorar 399" }).click();
    await expect(page.getByRole("heading", { name: "399 resultados" })).toBeVisible();
  });

  test("has no horizontal overflow and uses a closable evidence drawer on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/evidence/la-guaira");
    await expect(
      page.getByRole("heading", { name: "Lo que la evidencia permite sostener" }),
    ).toBeVisible();

    await page.getByRole("tab", { name: "Explorar 399" }).click();
    await expect(
      page.getByRole("heading", { name: "399 resultados" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Mostrar filtros" }),
    ).toBeVisible();
    await expect(
      page.getByRole("group", { name: "Observación" }),
    ).not.toBeVisible();

    await page.getByRole("button", { name: "Mostrar filtros" }).click();
    await expect(
      page.getByRole("group", { name: "Observación" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Ver resultados" }).click();

    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1);

    await page.locator("button").filter({ hasText: "pilot_" }).first().click();
    await expect(page.locator("#selected-cell-title")).toBeVisible();
    await page.getByRole("button", { name: "Cerrar detalle" }).click();
    await expect(page.locator("#selected-cell-title")).toHaveCount(0);
  });

  test("makes the complete atlas explicit from the ten-case timeline section", async ({ page }) => {
    await page.goto("/timeline");

    const link = page.getByRole("link", {
      name: /Explorar las 399 candidatas/,
    }).first();
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", "/evidence/la-guaira");
  });
});
